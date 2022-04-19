FROM python:3.8
MAINTAINER Jason Kulatunga <jason@thesparktree.com>

# Setup dependencies
RUN apt-get update \
 && apt-get -y install cron rsyslog git --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* \
 && sed -i 's/session    required     pam_loginuid.so/#session    required     pam_loginuid.so/' /etc/pam.d/cron

# Install dehydrated (letsencrypt client) & dns-lexicon
RUN git clone --depth 1 https://github.com/lukas2511/dehydrated.git /srv/dehydrated \
 && pip install dns-lexicon[full]

# Copy over dehydrated and & cron files
COPY ./examples/dehydrated.default.sh /srv/dehydrated/dehydrated.default.sh
COPY ./examples/crontab /etc/crontab
COPY ./examples/cron.sh /srv/dehydrated/cron.sh

# Configure dehydrated and Cron
# FIXME: This should be replaced with *your* domain name using a volume mount
RUN echo "test.intranet.example.com" > /srv/dehydrated/domains.txt \
 && chmod +x /srv/dehydrated/cron.sh \
 && crontab /etc/crontab \
 && touch /var/log/cron

CMD [ "/srv/dehydrated/cron.sh" ]
