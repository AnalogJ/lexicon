#!/usr/bin/env bash

rsyslogd
cron
tail -F /var/log/syslog /var/log/cron
