FROM ubuntu:trusty
MAINTAINER Kacper Kowalik <xarthisius.kk@gmail.com>

# Install RabbitMQ
RUN apt-get update && \
  apt-get install -qy python-setuptools python-urllib3 python-openssl python-httplib2 curl \
    rabbitmq-server logrotate cron wget python-pip python-cffi libpython-dev libssl-dev && \
  rabbitmq-plugins enable rabbitmq_management && \
  pip install python-etcd && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN rm -rf /usr/lib/python2.7/dist-packages/urllib3* && \
  pip install urllib3==1.9.1

# Installs Configuration Synchronization service
RUN cd /tmp && \
  wget https://pypi.python.org/packages/source/p/pyrabbit/pyrabbit-1.1.0.tar.gz && \
  tar xvf pyrabbit-1.1.0.tar.gz && cd pyrabbit-1.1.0 && \
  python setup.py install && \
  cd /tmp && rm -rf pyrabbit*


#RUN cd /tmp && \
#  wget https://github.com/jplana/python-etcd/archive/0.3.3.tar.gz && \
#  tar xvf 0.3.3.tar.gz && cd python-etcd-0.3.3/ && \
#  python setup.py install && \
#  cd /tmp && rm -rf 0.3.3.tar.gz python-etcd*

# Add and run scripts
ADD configure.sh /configure.sh
ADD configsync.py /configsync.py
ADD run.sh /run.sh
ADD logrotate.cron /etc/cron.daily/logrotate
ADD rabbitmq.logrotate /etc/logrotate.d/rabbitmq

RUN chmod 755 /configure.sh /configsync.py /run.sh /etc/cron.daily/logrotate
RUN /configure.sh

# RabbitMQ ports
EXPOSE 5672 15672

CMD ["/run.sh"]
