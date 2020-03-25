from lexicon.config import ConfigResolver
from lexicon.client import Client

lexicon_config = {
    "provider_name" : "cloudflare", # lexicon shortname for provider, see providers directory for available proviers
    "action": "list", # create, list, update, delete
    "domain": "capsulecd.com", # domain name
    "type": "CNAME", # specify a type for record filtering, case sensitive in some cases.
    "cloudflare": {
        # cloudflare(provider) specific configuration goes here.
        # if .with_env() is not used, all credentials required for authention must be specified here.
    }
}

config = ConfigResolver()
config.with_env().with_dict(dict_object=lexicon_config)
client = Client(config)
results = client.execute()
print results