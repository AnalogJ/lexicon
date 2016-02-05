# lexicon
Manipulate DNS records on various DNS providers in a standardized/agnostic way. 

## Introduction
Lexicon provides a way to manipulate DNS records on multiple DNS providers in a standardized way. 
Lexicon has a CLI but it can also be used as a python library. 

Lexicon was designed to be used in automation, specifically letsencrypt.

## Providers
Only DNS providers who have an API can be supported by `lexicon`. 

The current supported providers are:

- cloudflare ([docs](https://api.cloudflare.com/#endpoints))
- pointhq ([docs](https://pointhq.com/api/docs))

The next planned providers are:

- dnsimple
- pointhq
- namecheap
- route 53

## Setup
To use lexicon as a CLI application, do the following:
 
	git clone --depth 1 https://github.com/AnalogJ/lexicon.git
			
Using lexicon as a pip package is not yet supported.  	
	
## Usage

	$ python cli.py -h
	usage: cli.py [-h] [--name NAME] [--content CONTENT] [--ttl TTL]
				  [--priority PRIORITY] [--identifier IDENTIFIER]
				  [--auth-username AUTH_USERNAME] [--auth-password AUTH_PASSWORD]
				  [--auth-token AUTH_TOKEN] [--auth-otp-token AUTH_OTP_TOKEN]
				  {base,cloudflare,__init__} {create,list,update,delete} domain
				  {A,CNAME,MX,SOA,TXT}
	
	Create, Update, Delete, List DNS entries
	
	positional arguments:
	  {cloudflare}
							specify the DNS provider to use
	  {create,list,update,delete}
							specify the action to take
	  domain                specify the domain, supports subdomains as well
	  {A,CNAME,MX,SOA,TXT}  specify the entry type
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --name NAME           specify the record name
	  --content CONTENT     specify the record content
	  --ttl TTL             specify the record time-to-live
	  --priority PRIORITY   specify the record priority
	  --identifier IDENTIFIER
							specify the record for update or delete actions
	  --auth-username AUTH_USERNAME
							specify username used to authenticate to DNS provider
	  --auth-password AUTH_PASSWORD
							specify password used to authenticate to DNS provider
	  --auth-token AUTH_TOKEN
							specify token used authenticate to DNS provider
	  --auth-otp-token AUTH_OTP_TOKEN
							specify OTP/2FA token used authenticate to DNS
							provider

Using the lexicon CLI is pretty simple:

	# setup provider environmental variables:
	LEXICON_CLOUDFLARE_USERNAME="myusername@example.com"
	LEXICON_CLOUDFLARE_TOKEN="cloudflare-api-token"
	
	# list all TXT records on cloudflare
	python lexicon/cli.py cloudflare list example.com TXT
	
	# create a new TXT record on cloudflare
	python cli.py cloudflare create www.example.com TXT --name "_acme-challenge.www.example.com." --content "challenge token"

	# delete a  TXT record on cloudflare
	python cli.py cloudflare delete www.example.com TXT --name "_acme-challenge.www.example.com." --content "challenge token"
	python cli.py cloudflare delete www.example.com TXT --identifier "cloudflare record id"

	

### Letsencrypt Instructions
Lexicon has an example [letsencrypt.sh hook file](examples/letsencrypt.cloudflare.sh) that you can use for any supported provider. 
All you need to do is change the PROVIDER parameter. 

	letsencrypt.sh --cron --hook letsencrypt.cloudflare.sh --challenge dns-01
	

## TroubleShooting & Useful Tools
There is an included example Dockerfile that can be used to automatically generate certificates for your website.

## ToDo list
- Create and Register a lexicon pip package. 

## Contributing Changes.
If the DNS provider you use is not already available, please consider contributing by opening a pull request. 

## License
MIT

## References