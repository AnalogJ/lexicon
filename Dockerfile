FROM python:2
MAINTAINER Jason Kulatunga <jason@thesparktree.com>

# Setup dependencies
RUN apt-get update && \
	apt-get -y install cron rsyslog && \
	sed -i 's/session    required     pam_loginuid.so/#session    required     pam_loginuid.so/' /etc/pam.d/cron

# Install letsencrypt.sh & dns-lexicon
RUN git clone --depth 1 https://github.com/lukas2511/letsencrypt.sh.git /srv/letsencrypt && \
	pip install requests[security] dns-lexicon


# Copy over letsencrypt and & cron files
COPY ./examples/letsencrypt.default.sh /srv/letsencrypt/letsencrypt.default.sh
COPY ./examples/crontab /etc/crontab
COPY ./examples/cron.sh /srv/letsencrypt/cron.sh

# Configure Letsencrypt and Cron
# FIXME: This should be replaced with *your* domain name using a volume mount
RUN echo "test.intranet.example.com" > /srv/letsencrypt/domains.txt && \
	chmod +x /srv/letsencrypt/cron.sh && \
	crontab /etc/crontab && \
	touch /var/log/cron

CMD [ "/srv/letsencrypt/cron.sh" ]
