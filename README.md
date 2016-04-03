# lexicon
[![Circle CI](https://circleci.com/gh/AnalogJ/lexicon.svg?style=svg)](https://circleci.com/gh/AnalogJ/lexicon)
Manipulate DNS records on various DNS providers in a standardized/agnostic way. 

## Introduction
Lexicon provides a way to manipulate DNS records on multiple DNS providers in a standardized way. 
Lexicon has a CLI but it can also be used as a python library. 

Lexicon was designed to be used in automation, specifically letsencrypt.

## Providers
Only DNS providers who have an API can be supported by `lexicon`. 

The current supported providers are:

- Cloudflare ([docs](https://api.cloudflare.com/#endpoints))
- DNSimple ([docs](https://developer.dnsimple.com/))
- DnsMadeEasy ([docs](http://www.dnsmadeeasy.com/integration/pdf/API-Docv2.pdf))
- DNSPark ([docs](https://dnspark.zendesk.com/entries/31210577-REST-API-DNS-Documentation))
- EasyDNS ([docs](http://docs.sandbox.rest.easydns.net/))
- NS1 ([docs](https://ns1.com/api/))
- PointHQ ([docs](https://pointhq.com/api/docs))
- Rage4 ([docs](https://gbshouse.uservoice.com/knowledgebase/articles/109834-rage4-dns-developers-api))


Potential providers are as follows. If you would like to contribute one, please open a pull request.

- AHNames ([docs](https://ahnames.com/en/resellers?tab=2))
- AWS Route53 ([docs](https://docs.aws.amazon.com/Route53/latest/APIReference/Welcome.html))
- BuddyDNS ([docs](https://www.buddyns.com/support/api/v2/))
- ClouDNS ([docs](https://www.cloudns.net/wiki/article/56/))
- DigitalOcean ([docs](https://developers.digitalocean.com/documentation/v2/#create-a-new-domain))
- EntryDNS ([docs](https://entrydns.net/help))
- Google Cloud DNS ([docs](https://cloud.google.com/dns/api/v1/))
- ironDNS ([docs](https://www.irondns.net/download/soapapiguide.pdf;jsessionid=02A1029AA9FB8BACD2048A60F54668C0))
- Linode ([docs](https://www.linode.com/api/dns))
- Mythic Beasts([docs](https://www.mythic-beasts.com/support/api/primary))
- Namecheap ([docs](https://www.namecheap.com/support/api/methods.aspx))
- Namesilo ([docs](https://www.namesilo.com/api_reference.php))
- OnApp DNS ([docs](https://docs.onapp.com/display/3api/DNS+Zones))
- PowerDNS ([docs](https://doc.powerdns.com/md/httpapi/api_spec/))
- Rackspace ([docs](https://developer.rackspace.com/docs/cloud-dns/v1/developer-guide/))
- Transip ([docs](https://www.transip.nl/transip/api/))
- UltraDNS ([docs](https://restapi.ultradns.com/v1/docs))
- Yandex ([docs](https://tech.yandex.com/domain/doc/reference/dns-add-docpage/))
- Zerigo ([docs](https://www.zerigo.com/managed-dns/rest-api))
- Zonomi ([docs](http://zonomi.com/app/dns/dyndns.jsp))

## Setup
To use lexicon as a CLI application, do the following:
	
	pip install dns-lexicon

You can also install the latest version from the repository directly. 
 
	pip install git+https://github.com/AnalogJ/lexicon.git
			
## Usage

	$ lexicon -h
	usage: cli.py [-h] [--name NAME] [--content=CONTENT] [--ttl=TTL]
				  [--priority=PRIORITY] [--identifier=IDENTIFIER]
				  [--auth-username=AUTH_USERNAME] [--auth-password=AUTH_PASSWORD]
				  [--auth-token=AUTH_TOKEN] [--auth-otp-token=AUTH_OTP_TOKEN]
				  {cloudflare, dnsimple, dnsmadeeasy, nsone, pointhq} {create,list,update,delete} domain
				  {A,CNAME,MX,SOA,TXT}
	
	Create, Update, Delete, List DNS entries
	
	positional arguments:
	  {cloudflare, dnsimple, dnsmadeeasy, nsone, pointhq}
							specify the DNS provider to use
	  {create,list,update,delete}
							specify the action to take
	  domain                specify the domain, supports subdomains as well
	  {A,CNAME,MX,SOA,TXT}  specify the entry type
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --name=NAME           specify the record name
	  --content=CONTENT     specify the record content
	  --ttl=TTL             specify the record time-to-live
	  --priority=PRIORITY   specify the record priority
	  --identifier=IDENTIFIER
							specify the record for update or delete actions
	  --auth-username=AUTH_USERNAME
							specify username used to authenticate to DNS provider
	  --auth-password=AUTH_PASSWORD
							specify password used to authenticate to DNS provider
	  --auth-token=AUTH_TOKEN
							specify token used authenticate to DNS provider
	  --auth-otp-token=AUTH_OTP_TOKEN
							specify OTP/2FA token used authenticate to DNS
							provider

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

	

### Letsencrypt Instructions
Lexicon has an example [letsencrypt.sh hook file](examples/letsencrypt.default.sh) that you can use for any supported provider. 
All you need to do is set the PROVIDER env variable. 

	PROVIDER=cloudflare letsencrypt.sh --cron --hook letsencrypt.default.sh --challenge dns-01
	

## TroubleShooting & Useful Tools
There is an included example Dockerfile that can be used to automatically generate certificates for your website.

## ToDo list

- [x] Create and Register a lexicon pip package. 
- [ ] Write documentation on supported environmental variables. 
- [ ] Wire up automated release packaging on PRs.
- [ ] Check for additional dns hosts with apis (from [fog](http://fog.io/about/provider_documentation.html), [dnsperf](http://www.dnsperf.com/))

## Contributing Changes.
If the DNS provider you use is not already available, please consider contributing by opening a pull request. 

## License
MIT

## References

    tox

