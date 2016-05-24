FROM phusion/baseimage
MAINTAINER Jason Kulatunga <jason@thesparktree.com>

# Install Letsencrypt.sh deps + python deps + requests package deps
RUN \
  apt-get update && \
  apt-get install -y build-essential python-dev curl git nano wget libffi-dev libssl-dev && \
  rm -rf /var/lib/apt/lists/*


# Install pip
RUN curl --silent --show-error --retry 5 https://bootstrap.pypa.io/get-pip.py | sudo python2.7

# Clone letsencrypt.sh repo
RUN cd /srv && git clone --depth 1 https://github.com/lukas2511/letsencrypt.sh.git letsencrypt
RUN chmod +x /srv/letsencrypt/letsencrypt.sh

# Copy hooks
COPY ./examples/letsencrypt.default.sh /srv/letsencrypt/letsencrypt.default.sh
RUN chmod +x /srv/letsencrypt/letsencrypt.default.sh

# Install dns-lexicon
RUN pip install requests[security]
RUN pip install dns-lexicon

# Create letsencrypt domains.txt file.
RUN echo "test.intranet.example.com" > /srv/letsencrypt/domains.txt


CMD ["/srv/letsencrypt/letsencrypt.sh", "--cron", "--hook", "/srv/letsencrypt/letsencrypt.default.sh", "--challenge", "dns-01"]
#CMD /srv/letsencrypt/letsencrypt.sh --cron --hook /srv/letsencrypt/letsencrypt.default.sh --challenge dns-01

RUN \
  apt-get update && \
  apt-get install -y rsyslog && \
  rm -rf /var/lib/apt/lists/*
  
COPY ./examples/crontab /etc/crontab
RUN crontab /etc/crontab
COPY ./examples/cron.sh /srv/letsencrypt/cron.sh
RUN chmod +x /srv/letsencrypt/cron.sh
RUN touch /var/log/cron
CMD [ "/srv/letsencrypt/cron.sh" ]
