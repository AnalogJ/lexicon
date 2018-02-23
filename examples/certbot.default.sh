#!/usr/bin/env bash
#

set -euf -o pipefail

# ************** USAGE **************
#
# This is an example hook that can be used with Certbot.
#
# Example usage (with certbot-auto and this hook file saved in /root/):
#
#   sudo ./certbot-auto -d example.org -d www.example.org -a manual -i nginx --preferred-challenges dns \
#   --manual-auth-hook "/root/certbot.default.sh auth" --manual-cleanup-hook "/root/certbot.default.sh cleanup"
#
# This hook requires configuration, continue reading.
#
# ************** CONFIGURATION **************
#
# Please configure PROVIDER and PROVIDER_CREDENTIALS.
#
# PROVIDER:
#   Set this to whatever DNS host your domain is using:
#
#       route53 cloudflare cloudns cloudxns digitalocean 
#       dnsimple dnsmadeeasy dnspark dnspod easydns gandi 
#       glesys godaddy linode luadns memset namecheap namesilo 
#       nsone ovh pointhq powerdns rackspace rage4 softlayer 
#       transip vultr yandex zonomi
#
#   The full list is in Lexicon's README.
#   Defaults to Cloudflare.
#
PROVIDER="cloudflare"
#
# PROVIDER_CREDENTIALS:
#   Lexicon needs to know how to authenticate to your DNS Host.
#   This will vary from DNS host to host.
#   To figure out which flags to use, you can look at the Lexicon help.
#   For example, for help with Cloudflare:
#
#       lexicon cloudflare -h
#
PROVIDER_CREDENTIALS=("--auth-username=MY_USERNAME" "--auth-token=MY_API_KEY")
#
# PROVIDER_UPDATE_DELAY:
#   How many seconds to wait after updating your DNS records. This may be required,
#   depending on how slow your DNS host is to begin serving new DNS records after updating
#   them via the API. 30 seconds is a safe default, but some providers can be very slow 
#   (e.g. Linode).
#
#   Defaults to 30 seconds.
#
PROVIDER_UPDATE_DELAY=30

# To be invoked via Certbot's --manual-auth-hook
function auth {
    lexicon "${PROVIDER}" "${PROVIDER_CREDENTIALS[@]}" \
    create "${CERTBOT_DOMAIN}" TXT --name "_acme-challenge.${CERTBOT_DOMAIN}" --content "${CERTBOT_VALIDATION}"

    sleep "${PROVIDER_UPDATE_DELAY}"
}

# To be invoked via Certbot's --manual-cleanup-hook
function cleanup {
    lexicon "${PROVIDER}" "${PROVIDER_CREDENTIALS[@]}" \
    delete "${CERTBOT_DOMAIN}" TXT --name "_acme-challenge.${CERTBOT_DOMAIN}" --content "${CERTBOT_VALIDATION}"
}

HANDLER=$1; shift;
if [ -n "$(type -t $HANDLER)" ] && [ "$(type -t $HANDLER)" = function ]; then
  $HANDLER "$@"
fi