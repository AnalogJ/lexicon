import json
import requests

from lexicon.providers.base import Provider as BaseProvider

MANAGEMENT_URL = 'https://management.azure.com'
API_VERSION = '2018-03-01-preview'
NAMESERVER_DOMAINS = ['azure.com']


def provider_parser(subparser):
    subparser.add_argument('--auth-credentials')


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self._access_token = None
        self._subscription_id = None

        if self._get_provider_option('auth_credentials').startswith('file::'):
            with open(self._get_provider_option('auth_credentials')
                      .replace('file::', '')) as file_h:
                data = file_h.read()

        self._credentials = json.loads(data)

    def _authenticate(self):
        ad_endpoint = self._credentials['activeDirectoryEndpointUrl']
        tenant_id = self._credentials['tenantId']
        client_id = self._credentials['clientId']
        client_secret = self._credentials['clientSecret']
        self._subscription_id = self._credentials['subscriptionId']

        assert ad_endpoint
        assert tenant_id
        assert client_id
        assert client_secret
        assert self._subscription_id

        url = '{0}/{1}/oauth2/token'.format(ad_endpoint, tenant_id)
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'resource': MANAGEMENT_URL
        }

        result = requests.post(url, data=data)
        result.raise_for_status()

        self._access_token = result.json()['access_token']

        url = ('{0}/subscriptions/{1}/providers/Microsoft.Network/dnszones'
               .format(MANAGEMENT_URL, self._subscription_id))
        headers = {'Authorization': 'Bearer {0}'.format(self._access_token)}
        params = {'api-version': API_VERSION}

        result = requests.get(url, headers=headers, params=params)
        result.raise_for_status()

        print(result.json())

    def _request(self, action='GET', url='/', data=None, query_params=None):
        url = '{0}/subscriptions/{1}'