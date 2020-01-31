<p align="center">
  <a href="https://github.com/AnalogJ/lexicon">
  <img width="300" alt="lexicon_view" src="https://github.com/AnalogJ/lexicon/blob/master/logo.svg">
  </a>
</p>



# lexicon
Manipulate DNS records on various DNS providers in a standardized/agnostic way.

[![Build Status](https://dev.azure.com/AnalogJ/lexicon/_apis/build/status/AnalogJ.lexicon?branchName=master)](https://dev.azure.com/AnalogJ/lexicon/_build/latest?definitionId=1&branchName=master)
[![Coverage Status](https://coveralls.io/repos/github/AnalogJ/lexicon/badge.svg)](https://coveralls.io/github/AnalogJ/lexicon?branch=master)
[![Docker Pulls](https://img.shields.io/docker/pulls/analogj/lexicon.svg)](https://hub.docker.com/r/analogj/lexicon)
[![PyPI](https://img.shields.io/pypi/v/dns-lexicon.svg)](https://pypi.python.org/pypi/dns-lexicon)
[![PyPI](https://img.shields.io/pypi/pyversions/dns-lexicon.svg)](https://pypi.python.org/pypi/dns-lexicon)
[![GitHub license](https://img.shields.io/github/license/AnalogJ/lexicon.svg)](https://github.com/AnalogJ/lexicon/blob/master/LICENSE)

## Introduction
Lexicon provides a way to manipulate DNS records on multiple DNS providers in a standardized way.
Lexicon has a CLI but it can also be used as a python library.

Lexicon was designed to be used in automation, specifically letsencrypt.

- [Generating Intranet & Private Network SSL Certificates using Lets Encrypt & Lexicon](http://blog.thesparktree.com/post/138999997429/generating-intranet-and-private-network-ssl)

## Providers
Only DNS providers who have an API can be supported by `lexicon`.

The current supported providers are:

- Aliyun.com ([docs](https://help.aliyun.com/document_detail/29739.html))
- AuroraDNS ([docs](https://www.pcextreme.com/aurora/dns))
- AWS Route53 ([docs](https://docs.aws.amazon.com/Route53/latest/APIReference/Welcome.html))
- Azure DNS ([docs](https://docs.microsoft.com/en-us/rest/api/dns/))
- Cloudflare ([docs](https://api.cloudflare.com/#endpoints))
- ClouDNS ([docs](https://www.cloudns.net/wiki/article/56/))
- CloudXNS ([docs](https://www.cloudxns.net/Support/lists/cid/17.html))
- ConoHa ([docs](https://www.conoha.jp/docs/))
- Constellix ([docs](https://api-docs.constellix.com/?version=latest))
- DigitalOcean ([docs](https://developers.digitalocean.com/documentation/v2/#create-a-new-domain))
- Dinahosting ([docs](https://en.dinahosting.com/api))
- DirectAdmin ([docs](https://www.directadmin.com/features.php?id=504))
- DNSimple (docs: [v1](https://developer.dnsimple.com/), [v2](https://developer.dnsimple.com/v2/))
- DnsMadeEasy ([docs](https://api-docs.dnsmadeeasy.com/?version=latest))
- DNSPark ([docs](https://dnspark.zendesk.com/entries/31210577-REST-API-DNS-Documentation))
- DNSPod ([docs](https://support.dnspod.cn/Support/api))
- Dreamhost ([docs](https://help.dreamhost.com/hc/en-us/articles/217560167-API_overview))
- Dynu ([docs](https://www.dynu.com/Support/API))
- EasyDNS ([docs](http://docs.sandbox.rest.easydns.net/))
- Easyname ([docs](https://www.easyname.com/en))
- EUserv ([docs](https://support.euserv.com/api-doc/))
- ExoScale ([docs](https://community.exoscale.com/documentation/dns/api/))
- Gandi (docs: [RPC (old)](http://doc.rpc.gandi.net/) / [LiveAPI](http://doc.livedns.gandi.net/))
- Gehirn ([docs](https://support.gehirn.jp/apidocs/gis/dns/index.html))
- Glesys ([docs](https://github.com/glesys/API/wiki/))
- GoDaddy ([docs](https://developer.godaddy.com/getstarted#access))
- Google Cloud DNS ([docs](https://cloud.google.com/dns/api/v1/))
- Gransy (sites subreg.cz, regtons.com and regnames.eu, [docs](https://subreg.cz/manual/))
- Hover ([docs](https://hoverapi.docs.apiary.io/))
- Hurricane Electric DNS ([docs](https://dns.he.net/))
- Hetzner ([docs](https://dns.hetzner.com/api-docs/))
- Infoblox ([docs](https://docs.infoblox.com/display/ILP/Infoblox+Documentation+Portal))
- Internet.bs ([docs](https://internetbs.net/ResellerRegistrarDomainNameAPI))
- INWX ([docs](https://www.inwx.de/en/offer/api))
- Linode ([docs](https://www.linode.com/api/dns))
- Linode v4 ([docs](https://developers.linode.com/api/docs/v4#tag/Domains))
- LuaDNS ([docs](http://www.luadns.com/api.html))
- Memset ([docs](https://www.memset.com/apidocs/methods_dns.html))
- Namecheap ([docs](https://www.namecheap.com/support/api/methods.aspx))
- Namesilo ([docs](https://www.namesilo.com/api_reference.php))
- Netcup ([docs](https://ccp.netcup.net/run/webservice/servers/endpoint.php))
- NFSN (NearlyFreeSpeech)
- NS1 ([docs](https://ns1.com/api/))
- OnApp ([docs](https://docs.onapp.com/display/55API/OnApp+5.5+API+Guide))
- Online
- OVH ([docs](https://api.ovh.com/))
- Plesk ([docs](https://docs.plesk.com/en-US/onyx/api-rpc/about-xml-api.28709/))
- PointHQ ([docs](https://pointhq.com/api/docs))
- PowerDNS ([docs](https://doc.powerdns.com/md/httpapi/api_spec/))
- Rackspace ([docs](https://developer.rackspace.com/docs/cloud-dns/v1/developer-guide/))
- Rage4 ([docs](https://gbshouse.uservoice.com/knowledgebase/articles/109834-rage4-dns-developers-api))
- RcodeZero ([docs](https://my.rcodezero.at/api-doc))
- Sakura Cloud by SAKURA Internet Inc. ([docs](https://developer.sakura.ad.jp/cloud/api/1.1/))
- SafeDNS by UKFast ([docs](https://developers.ukfast.io/documentation/safedns))
- SoftLayer ([docs](https://sldn.softlayer.com/article/REST#HTTP_Request_Types))
- Subreg (deprecated, use Gransy)
- Transip ([docs](https://www.transip.nl/transip/api/))
- UltraDNS ([docs](https://ultra-portalstatic.ultradns.com/static/docs/REST-API_User_Guide.pdf))
- Vultr ([docs](https://www.vultr.com/api/))
- Yandex ([docs](https://tech.yandex.com/domain/doc/reference/dns-add-docpage/))
- Zeit ([docs](https://zeit.co/api#post-domain-records))
- Zilore ([docs](https://zilore.com/en/help/api))
- Zonomi ([docs](http://zonomi.com/app/dns/dyndns.jsp))

Potential providers are as follows. If you would like to contribute one, follow the [CONTRIBUTING.md](https://github.com/AnalogJ/lexicon/blob/master/CONTRIBUTING.md) and then open a pull request.

- AHNames ([docs](https://ahnames.com/en/resellers?tab=2))
- ~~DurableDNS ([docs](https://durabledns.com/wiki/doku.php/ddns))~~ <sub>Can't set TXT records</sub>
- cyon.ch
- Dyn ([docs](https://help.dyn.com/dns-api-knowledge-base/)) :dollar: <sub>requires paid account</sub>
- EntryDNS ([docs](https://entrydns.net/help)) :dollar: <sub>requires paid account</sub>
- FreeDNS ([docs](https://freedns.afraid.org/scripts/freedns.clients.php))
- Host Virtual DNS ([docs](https://github.com/hostvirtual/hostvirtual-python-sdk/blob/master/hostvirtual.py)) :dollar: <sub>requires paid account</sub>
- HostEurope
- Infoblox NIOS
- ironDNS ([docs](https://www.irondns.net/download/soapapiguide.pdf;jsessionid=02A1029AA9FB8BACD2048A60F54668C0)) :dollar: <sub>requires paid account</sub>
- ISPConfig
- InternetX autoDNS ([docs](https://internetx.com))
- Knot DNS
- KingHost
- Liquidweb ([docs](https://www.liquidweb.com/storm/api/docs/v1/Network/DNS/Zone.html)) :dollar: <sub>requires paid account</sub>
- Loopia ([docs](https://www.loopia.com/api/)) :dollar: <sub>requires paid account</sub>
- Mythic Beasts([docs](https://www.mythic-beasts.com/support/api/primary))
- NFSN (NearlyFreeSpeech) ([docs](https://api.nearlyfreespeech.net/)) :dollar: <sub>requires paid account</sub>
- RFC2136 ([docs](https://en.wikipedia.org/wiki/Dynamic_DNS))
- Servercow ([docs](https://servercow.de))
- selectel.com
- TELE3 ([docs](https://www.tele3.cz))
- UltraDNS ([docs](https://restapi.ultradns.com/v1/docs)) :dollar: <sub>requires paid account</sub>
- UnoEuro API
- VSCALE
- WorldWideDns ([docs](https://www.worldwidedns.net/dns_api_protocol.asp)) :dollar: <sub>requires paid account</sub>
- Zerigo ([docs](https://www.zerigo.com/managed-dns/rest-api)) :dollar: <sub>requires paid account</sub>
- Zoneedit ([docs](http://forum.zoneedit.com/index.php?threads/dns-update-api.419/))
- __Any others I missed__

## Setup

**Warning: it is strongly advised with pip to install Lexicon in a Python virtual environment, in order to avoid interference
between Python modules preinstalled on your system as OS packages and modules installed by pip (see https://docs.python-guide.org/dev/virtualenvs/).**

To use lexicon as a CLI application, do the following:

    pip install dns-lexicon

Some providers (like Route53 and TransIP) require additional dependencies. You can install [provider specific dependencies](https://github.com/AnalogJ/lexicon/blob/master/setup.py#L34-L44) separately:

    pip install dns-lexicon[route53]

To install lexicon with the additional dependencies of every provider, do the following:

    pip install dns-lexicon[full]

You can also install the latest version from the repository directly.

    pip install git+https://github.com/AnalogJ/lexicon.git

and with Route 53 provider dependencies:

    pip install git+https://github.com/AnalogJ/lexicon.git#egg=dns-lexicon[route53]

*As an alternative you can also install Lexicon using the OS packages available for major Linux distributions (see `lexicon` or `dns-lexicon` package in https://pkgs.org/download/lexicon).*

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
    export LEXICON_CLOUDFLARE_USERNAME="myusername@example.com"
    export LEXICON_CLOUDFLARE_TOKEN="cloudflare-api-token"

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

#### Authentication

Instead of providing Authentication information via the CLI, you can also specify them via Environmental Variables.
Every DNS service and auth flag maps to an Environmental Variable as follows: `LEXICON_{DNS Provider Name}_{Auth Type}`

So instead of specifying `--auth-username` and `--auth-token` flags when calling `lexicon cloudflare ...`,
you could instead set the `LEXICON_CLOUDFLARE_USERNAME` and `LEXICON_CLOUDFLARE_TOKEN` environmental variables.

If you've got a subdomain delegation configured and need records configured within that (eg, you're trying to set `test.foo.example.com` where `foo.example.com` is configured as a separate zone), set `LEXICON_DELEGATED` to the delegated domain.

    LEXICON_DELEGATED=foo.example.com

#### TLD Cache

The [tldextract](https://pypi.org/project/tldextract/) library is used by Lexicon to find the actual domain name
from the provided FQDN (eg. `domain.net` is the actual domain in `www.domain.net`). Lexicon stores `tldextract` cache
by default in `~/.lexicon_tld_set` where `~` is the current user's home directory. You can change this path using
the `LEXICON_TLDEXTRACT_CACHE` environment variable.

For instance, to store `tldextract` cache in `/my/path/to/tld_cache`, you can invoke Lexicon like this from a Linux shell:

    LEXICON_TLDEXTRACT_CACHE=/my/path/to/tld_cache lexicon myprovider create www.example.net TXT ...

### Letsencrypt Instructions
Lexicon has an example [dehydrated hook file](examples/dehydrated.default.sh) that you can use for any supported provider.
All you need to do is set the PROVIDER env variable.

    PROVIDER=cloudflare dehydrated --cron --hook dehydrated.default.sh --challenge dns-01

Lexicon can also be used with [Certbot](https://certbot.eff.org/) and the included [Certbot hook file](examples/certbot.default.sh) (requires configuration).

## TroubleShooting & Useful Tools
There is an included example Dockerfile that can be used to automatically generate certificates for your website.

## ToDo list

- [x] Create and Register a lexicon pip package.
- [ ] Write documentation on supported environmental variables.
- [x] Wire up automated release packaging on PRs.
- [x] Check for additional dns hosts with apis (from [fog](http://fog.io/about/provider_documentation.html), [dnsperf](http://www.dnsperf.com/), [libcloud](https://libcloud.readthedocs.io/en/latest/dns/supported_providers.html))
- [ ] Get a list of Letsencrypt clients, and create hook files for them ([letsencrypt clients](https://github.com/letsencrypt/letsencrypt/wiki/Links))

## Contributing Changes.
If the DNS provider you use is not already available, please consider contributing by opening a pull request and
following the [CONTRIBUTING.md](https://github.com/AnalogJ/lexicon/blob/master/CONTRIBUTING.md)

## License
- MIT
- [Logo: transform by Mike Rowe from the Noun Project](https://thenounproject.com/term/transform/397964)


## References

    tox

