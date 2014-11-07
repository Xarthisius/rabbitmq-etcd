FROM debian:sid
MAINTAINER Kacper Kowalik <xarthisius.kk@gmail.com>

# Install RabbitMQ
RUN apt-get update && \
    apt-get install -y rabbitmq-server curl sudo python-dev python-pip logrotate cron && \
    rabbitmq-plugins enable rabbitmq_management && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Installs Configuration Synchronization service
RUN pip2 install python-etcd urllib3 pyrabbit

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
