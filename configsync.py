#!/usr/bin/env python2
from __future__ import print_function

import os
import sys
import etcd
import json
import time
import base64
import pyrabbit.api
import urllib3.exceptions
from collections import defaultdict

PREFIX = '/rabbitmq'

def filter_prefix(d, pref):
    return [k for k in d.keys() if k.startswith("%s/%s/" % (PREFIX, pref))]

class log:
    @staticmethod
    def info(msg):
        print("=> " + msg)
    @staticmethod
    def error(msg, e=None):
        print("=! %s : %s" % (msg, str(e)), file=sys.stderr)

class State:
    def __init__(self):
        self.vhosts = set()
        self.users = set()
        self.permissions = defaultdict(lambda: defaultdict(lambda: None))

class Config:
    def __init__(self):
        self.client = pyrabbit.api.Client('localhost:15672', 'guest', 'guest')
        self.state = State()

    def refresh(self):
        fresh_vhosts = set(self.client.get_vhost_names())
        self.state.vhosts.update(fresh_vhosts)

    def sync(self, children):
        etc = dict((child.key, child.value) for child in children)

        vhosts = set(k.split('/')[-1] for k in filter_prefix(etc, 'vhosts'))
        self.sync_vhosts(vhosts)

        users = dict((k.split('/')[-1], etc[k]) for k in filter_prefix(etc, 'users'))
        self.sync_users(users, etc)

        permissions = [tuple(k.split('/')[-2:] + [etc[k]]) for k in filter_prefix(etc, 'permissions')]
        self.sync_permissions(permissions)

    def sync_vhosts(self, vhosts):
        vhosts_to_add = vhosts - self.state.vhosts
        for vhost in vhosts_to_add:
            log.info("Creating vhost %s" % vhost)
            try:
                self.client.create_vhost(vhost)
                self.state.vhosts.add(vhost)
            except Exception as e:
                log.error("Failed to create vhost %s" % vhost, e)
        vhosts_to_rm = self.state.vhosts - vhosts - {'/'}
        for vhost in vhosts_to_rm:
            log.info("Removing vhost %s" % vhost)
            try:
                self.client.delete_vhost(vhost)
                self.state.vhosts.remove(vhost)
            except Exception as e:
                log.error("Failed to remove vhost %s" % vhost, e)

    def sync_users(self, users, etc):
        user_set = set(users.keys())
        users_to_add = user_set - self.state.users
        for user in users_to_add:
            tags = etc.get(PREFIX + '/tags/' + user, '')
            log.info("Creating user %s:%s with tags %s" % (user, users[user], tags))
            try:
                self.client.create_user(user, users[user], tags)
                self.state.users.add(user)
            except Exception as e:
                log.error("Failed to create user %s" % user, e)
        users_to_rm = self.state.users - user_set - {'guest'}
        for user in users_to_rm:
            log.info("Removing user %s" % user)
            try:
                self.client.delete_user(user)
                self.state.users.remove(user)
            except Exception as e:
                log.error("Failed to remove user %s" % user, e)

    def sync_permissions(self, permissions):
        for (vhost, user, perm) in permissions:
            if self.state.permissions[vhost][user] != perm:
                log.info("Setting permissions for %s on %s to %s" % (vhost, user, perm))
                try:
                    self.client.set_vhost_permissions(vhost, user, *perm.split('/'))
                    self.state.permissions[vhost][user] = perm
                except Exception as e:
                    log.error("Failed to set permissions for %s" % user, e)

if __name__ == '__main__':
    host_ip = os.environ.get('COREOS_PRIVATE_IPV4', None)
    log.info("Connecting to etcd at %s" % host_ip)

    init = False
    client = etcd.Client(host=host_ip, port=4001)
    config = Config()

    client.set(PREFIX + '/service', json.dumps({'host': host_ip, 'port': 5672}))

    while True:
        try:
            if not init:
                r = client.read(PREFIX, recursive=True)
                init = True
            else:
                client.read(PREFIX, recursive=True, wait=True)
                r = client.read(PREFIX, recursive=True)
            config.refresh()
            config.sync(r.children)
        except urllib3.exceptions.ReadTimeoutError as e:
            time.sleep(1)
        except KeyError as e:
            time.sleep(1)
        except etcd.EtcdException as e:
            time.sleep(1)

