[![Circle CI](https://circleci.com/gh/AnalogJ/lexicon.svg?style=shield)](https://circleci.com/gh/AnalogJ/lexicon)
[![Coverage Status](https://coveralls.io/repos/github/AnalogJ/lexicon/badge.svg)](https://coveralls.io/github/AnalogJ/lexicon?branch=master)
[![Docker Pulls](https://img.shields.io/docker/pulls/analogj/lexicon.svg)](https://hub.docker.com/r/analogj/lexicon)
[![PyPI](https://img.shields.io/pypi/v/dns-lexicon.svg)](https://pypi.python.org/pypi/dns-lexicon)
[![PyPI](https://img.shields.io/pypi/pyversions/dns-lexicon.svg)](https://pypi.python.org/pypi/dns-lexicon)
[![GitHub license](https://img.shields.io/github/license/AnalogJ/lexicon.svg)](https://github.com/AnalogJ/lexicon/blob/master/LICENSE)

# lexicon
Manipulate DNS records on various DNS providers in a standardized/agnostic way.

## Introduction
Lexicon provides a way to manipulate DNS records on multiple DNS providers in a standardized way.
Lexicon has a CLI but it can also be used as a python library.

Lexicon was designed to be used in automation, specifically letsencrypt.

- [Generating Intranet & Private Network SSL Certificates using Lets Encrypt & Lexicon](http://blog.thesparktree.com/post/138999997429/generating-intranet-and-private-network-ssl)

## Providers
Only DNS providers who have an API can be supported by `lexicon`.

The current supported providers are:

- AWS Route53 ([docs](https://docs.aws.amazon.com/Route53/latest/APIReference/Welcome.html))
- Cloudflare ([docs](https://api.cloudflare.com/#endpoints))
- CloudXNS ([docs](https://www.cloudxns.net/Support/lists/cid/17.html))
- DigitalOcean ([docs](https://developers.digitalocean.com/documentation/v2/#create-a-new-domain))
- DNSimple ([docs](https://developer.dnsimple.com/))
- DnsMadeEasy ([docs](http://www.dnsmadeeasy.com/pdf/API-Docv2.pdf))
- DNSPark ([docs](https://dnspark.zendesk.com/entries/31210577-REST-API-DNS-Documentation))
- DNSPod ([docs](https://support.dnspod.cn/Support/api))
- EasyDNS ([docs](http://docs.sandbox.rest.easydns.net/))
- Gandi ([docs](http://doc.rpc.gandi.net/))
- Glesys ([docs](https://github.com/glesys/API/wiki/functions_domain))
- GoDaddy ([docs](https://developer.godaddy.com/getstarted#access))
- LuaDNS ([docs](http://www.luadns.com/api.html))
- Memset ([docs](https://www.memset.com/apidocs/methods_dns.html))
- Namesilo ([docs](https://www.namesilo.com/api_reference.php))
- NS1 ([docs](https://ns1.com/api/))
- OVH ([docs](https://api.ovh.com/))
- PointHQ ([docs](https://pointhq.com/api/docs))
- PowerDNS ([docs](https://doc.powerdns.com/md/httpapi/api_spec/))
- Rage4 ([docs](https://gbshouse.uservoice.com/knowledgebase/articles/109834-rage4-dns-developers-api))
- Transip ([docs](https://www.transip.nl/transip/api/))
- Yandex ([docs](https://tech.yandex.com/domain/doc/reference/dns-add-docpage/))
- Vultr ([docs](https://www.vultr.com/api/))

Potential providers are as follows. If you would like to contribute one, please open a pull request.

- AuroraDNS ([docs](https://www.pcextreme.com/aurora/dns))
- AHNames ([docs](https://ahnames.com/en/resellers?tab=2))
- ~~BuddyDNS ([docs](https://www.buddyns.com/support/api/v2/))~~
- ~~ClouDNS ([docs](https://www.cloudns.net/wiki/article/56/))~~ <sub>Unable to test, requires paid account</sub>
- ~~DurableDNS ([docs](https://durabledns.com/wiki/doku.php/ddns))~~ <sub>Can't set TXT records</sub>
- ~~Dyn ([docs](https://help.dyn.com/dns-api-knowledge-base/))~~ <sub>Unable to test, requires paid account</sub>
- ~~EntryDNS ([docs](https://entrydns.net/help))~~ <sub>Unable to test, requires paid account</sub>
- Google Cloud DNS ([docs](https://cloud.google.com/dns/api/v1/))
- ~~Host Virtual DNS ([docs](https://github.com/hostvirtual/hostvirtual-python-sdk/blob/master/hostvirtual.py))~~ <sub>Unable to test, requires paid account</sub>
- ~~ironDNS ([docs](https://www.irondns.net/download/soapapiguide.pdf;jsessionid=02A1029AA9FB8BACD2048A60F54668C0))~~ <sub>Unable to test, requires paid account</sub>
- ~~Linode ([docs](https://www.linode.com/api/dns))~~ <sub>Unable to test, requires paid account</sub>
- ~~Liquidweb ([docs](https://www.liquidweb.com/storm/api/docs/v1/Network/DNS/Zone.html))~~ <sub>Unable to test, requires paid account</sub>
- Mythic Beasts([docs](https://www.mythic-beasts.com/support/api/primary))
- Namecheap ([docs](https://www.namecheap.com/support/api/methods.aspx))
- ~~NFSN (NearlyFreeSpeech) ([docs](https://api.nearlyfreespeech.net/))~~ <sub>Unable to test, requires paid account</sub>
- ~~OnApp DNS ([docs](https://docs.onapp.com/display/3api/DNS+Zones))~~ <sub>Unable to test, requires paid account</sub>
- Rackspace ([docs](https://developer.rackspace.com/docs/cloud-dns/v1/developer-guide/))
- RFC2136 ([docs](https://en.wikipedia.org/wiki/Dynamic_DNS))
- SoftLayer ([docs](https://sldn.softlayer.com/article/REST#HTTP_Request_Types))
- ~~UltraDNS ([docs](https://restapi.ultradns.com/v1/docs))~~ <sub>Unable to test, requires paid account</sub>
- ~~WorldWideDns ([docs](https://www.worldwidedns.net/dns_api_protocol.asp))~~ <sub>Unable to test, requires paid account</sub>
- ~~Zerigo ([docs](https://www.zerigo.com/managed-dns/rest-api))~~ <sub>Unable to test, requires paid account</sub>
- ~~Zonomi ([docs](http://zonomi.com/app/dns/dyndns.jsp))~~ <sub>Unable to test, requires paid account</sub>

## Setup
To use lexicon as a CLI application, do the following:

    pip install dns-lexicon

Some providers (like Route53 and TransIP) require additional dependencies. You can install provider specific dependencies separately:

    pip install dns-lexicon[route53]

You can also install the latest version from the repository directly.

    pip install git+https://github.com/AnalogJ/lexicon.git

and with Route 53 provider dependencies:

    pip install git+https://github.com/AnalogJ/lexicon.git#egg=dns-lexicon[route53]

## Usage

    $ lexicon -h
      usage: lexicon [-h] [--version] [--delegated DELEGATED]
                     {cloudflare,cloudxns,digitalocean,dnsimple,dnsmadeeasy,dnspark,dnspod,easydns,luadns,namesilo,nsone,pointhq,rage4,route53,vultr,yandex,zonomi}
                     ...

      Create, Update, Delete, List DNS entries

      positional arguments:
        {cloudflare,cloudxns,digitalocean,dnsimple,dnsmadeeasy,dnspark,dnspod,easydns,luadns,namesilo,nsone,pointhq,rage4,route53,vultr,yandex,zonomi}
                              specify the DNS provider to use
          cloudflare          cloudflare provider
          cloudxns            cloudxns provider
          digitalocean        digitalocean provider
        ...
          rage4               rage4 provider
          route53             route53 provider
          vultr               vultr provider
          yandex              yandex provider
          zonomi              zonomi provider

      optional arguments:
        -h, --help            show this help message and exit
        --version             show the current version of lexicon
        --delegated DELEGATED
                              specify the delegated domain


      $ lexicon cloudflare -h
      usage: lexicon cloudflare [-h] [--name NAME] [--content CONTENT] [--ttl TTL]
                                [--priority PRIORITY] [--identifier IDENTIFIER]
                                [--auth-username AUTH_USERNAME]
                                [--auth-token AUTH_TOKEN]
                                {create,list,update,delete} domain
                                {A,AAAA,CNAME,MX,NS,SPF,SOA,TXT,SRV,LOC}

      positional arguments:
        {create,list,update,delete}
                              specify the action to take
        domain                specify the domain, supports subdomains as well
        {A,AAAA,CNAME,MX,NS,SPF,SOA,TXT,SRV,LOC}
                              specify the entry type

      optional arguments:
        -h, --help            show this help message and exit
        --name NAME           specify the record name
        --content CONTENT     specify the record content
        --ttl TTL             specify the record time-to-live
        --priority PRIORITY   specify the record priority
        --identifier IDENTIFIER
                              specify the record for update or delete actions
        --auth-username AUTH_USERNAME
                              specify email address used to authenticate
        --auth-token AUTH_TOKEN
                              specify token used authenticate

Using the lexicon CLI is pretty simple:

    # setup provider environmental variables:
    LEXICON_CLOUDFLARE_USERNAME="myusername@example.com"
    LEXICON_CLOUDFLARE_TOKEN="cloudflare-api-token"

    # list all TXT records on cloudflare
    lexicon cloudflare list example.com TXT

    # create a new TXT record on cloudflare
    lexicon cloudflare create www.example.com TXT --name="_acme-challenge.www.example.com." --content="challenge token"

    # delete a  TXT record on cloudflare
    lexicon cloudflare delete www.example.com TXT --name="_acme-challenge.www.example.com." --content="challenge token"
    lexicon cloudflare delete www.example.com TXT --identifier="cloudflare record id"

## Authentication
Most supported DNS services provide an API token, however each service implements authentication differently.
Lexicon attempts to standardize authentication around the following CLI flags:

- `--auth-username` - For DNS services that require it, this is usually the account id or email address
- `--auth-password` - For DNS services that do not provide an API token, this is usually the account password
- `--auth-token` - This is the most common auth method, the API token provided by the DNS service

You can see all the `--auth-*` flags for a specific service by reading the DNS service specific help: `lexicon cloudflare -h`

### Environmental Variables
Instead of providing Authentication information via the CLI, you can also specify them via Environmental Variables.
Every DNS service and auth flag maps to an Environmental Variable as follows: `LEXICON_{DNS Provider Name}_{Auth Type}`

So instead of specifying `--auth-username` and `--auth-token` flags when calling `lexicon cloudflare ...`,
you could instead set the `LEXICON_CLOUDFLARE_USERNAME` and `LEXICON_CLOUDFLARE_TOKEN` environmental variables.

### Letsencrypt Instructions
Lexicon has an example [dehydrated hook file](examples/dehydrated.default.sh) that you can use for any supported provider.
All you need to do is set the PROVIDER env variable.

    PROVIDER=cloudflare dehydrated --cron --hook dehydrated.default.sh --challenge dns-01


## TroubleShooting & Useful Tools
There is an included example Dockerfile that can be used to automatically generate certificates for your website.

## ToDo list

- [x] Create and Register a lexicon pip package.
- [ ] Write documentation on supported environmental variables.
- [x] Wire up automated release packaging on PRs.
- [x] Check for additional dns hosts with apis (from [fog](http://fog.io/about/provider_documentation.html), [dnsperf](http://www.dnsperf.com/), [libcloud](https://libcloud.readthedocs.io/en/latest/dns/supported_providers.html))
- [ ] Get a list of Letsencrypt clients, and create hook files for them ([letsencrypt clients](https://github.com/letsencrypt/letsencrypt/wiki/Links))

## Contributing Changes.
If the DNS provider you use is not already available, please consider contributing by opening a pull request.

## License
MIT

## References

    tox
    
    
