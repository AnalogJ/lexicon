#!/usr/bin/env bash

#
# Example how to deploy a DNS challange using lexicon
#

set -e
set -u
set -o pipefail

PROVIDER="cloudflare"
done="no"

if [[ "$1" = "deploy_challenge" ]]; then
	echo "deploy_challenge called: ${1}, ${2}, ${3}, ${4}"
    /srv/lexicon/cli.py $PROVIDER create ${2} TXT --name "_acme-challenge.${2}." --content "${4}"
    done="yes"
fi

if [[ "$1" = "clean_challenge" ]]; then
	echo "clean_challenge called: ${1}, ${2}, ${3}, ${4}"
	/srv/lexicon/cli.py $PROVIDER delete ${2} TXT --name "_acme-challenge.${2}." --content "${4}"
    done="yes"
fi

if [[ "${1}" = "deploy_cert" ]]; then
	echo "deploy_cert called: ${1}, ${2}, ${3}, ${4}"
    done="yes"
fi

if [[ ! "${done}" = "yes" ]]; then
    echo Unkown hook "${1}"
    exit 1
fi

sleep 30
exit 0