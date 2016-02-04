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

# Create lexicon folder
COPY ./lexicon /srv/lexicon
COPY ./requirements.txt  /srv/lexicon
RUN chmod +x /srv/lexicon/cli.py
RUN pip install -r /srv/lexicon/requirements.txt

# Copy hooks
COPY ./examples/letsencrypt.cloudflare.sh /srv/letsencrypt/letsencrypt.cloudflare.sh
RUN chmod +x /srv/letsencrypt/letsencrypt.cloudflare.sh

# Create letsencrypt domains.txt file.
RUN echo "test.example.com" > /srv/letsencrypt/domains.txt


CMD ["bash"]
#CMD /srv/letsencrypt/letsencrypt.sh --cron --hook /srv/letsencrypt/letsencrypt.cloudflare.sh --challenge dns-01
