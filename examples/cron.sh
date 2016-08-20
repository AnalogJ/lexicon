#!/usr/bin/env bash

env > /etc/profile
rsyslogd
cron
tail -F /var/log/syslog /var/log/cron
