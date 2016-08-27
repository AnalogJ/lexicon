#!/usr/bin/env bash

env > /etc/environment
rsyslogd
cron
tail -F /var/log/syslog /var/log/cron
