from base_libcloud import Provider as BaseLibcloudProvider
import requests
import json

def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify email address used to authenticate")
    subparser.add_argument("--auth-token", help="specify token used authenticate")

class Provider(BaseLibcloudProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.provider_name = 'cloudflare'
        self.driver = self.driver_cls(self.options['auth_username'], self.options.get('auth_token'))
