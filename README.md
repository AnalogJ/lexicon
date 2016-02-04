# lexicon
Manipulate DNS records on various DNS providers in a standardized/agnostic way. 

## Introduction
Lexicon provides a way to manipulate DNS records on multiple DNS providers in a standardized way. 
Lexicon has a CLI but it can also be used as a python library. 

Lexicon was designed to be used in automation, specifically letsencrypt.

## Providers
Only DNS providers who have an API can be supported by `lexicon`. 

The current supported providers are:

-  cloudflare

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
To change between providers, all you need to do is change the provider parameter, and update configuration. 

	# setup provider environmental variables:
	LEXICON_CLOUDFLARE_USERNAME="myusername@example.com"
	LEXICON_CLOUDFLARE_TOKEN="cloudflare-api-token"
	
	# list all TXT records on cloudflare
	python lexicon/cli.py cloudflare list example.com TXT
	

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