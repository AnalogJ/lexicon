"""Module provider for DirectAdmin hosts"""
import logging
import requests

from lexicon.providers.base import Provider as BaseProvider
from requests.auth import HTTPBasicAuth

LOGGER = logging.getLogger(__name__)

def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument(
        "--auth-password",
        help = "specify password for authentication (or login key in case of two-factor-authentication)"
    )

    subparser.add_argument(
        "--auth-username",
        help = "specify username for authentication"
    )

    subparser.add_argument(
        "--endpoint",
        help = "specify the DirectAdmin endpoint"
    )

# See https://www.directadmin.com/features.php?id=504 for the specification of
# the URIs for the different operations
class Provider(BaseProvider):
    """Provider class for DirectAdmin"""
    def __init__(self, config):
        super(Provider, self).__init__(config)

        self.endpoint = self._get_provider_option('endpoint')
        if self.endpoint is None:
            raise Exception('Specify endpoint of DirectAdmin')

    def _authenticate(self):
        try:
            response = self._get()
        except requests.exceptions.HTTPError as err:
            # A 401 error will be returned in case of incorrect or missing
            # credentials
            cause = err.response.json()['error']
            raise Exception(cause)

    def _create_record(self, rtype, name, content):
        None

    def _list_records(self, rtype=None, name=None, content=None):
        response = { 'records': [] }
        try:
            response = self._get()
        except requests.exceptions.HTTPError as err:
            print(err.response.text)
            raise

        records = response['records']
        if rtype:
            records = [ record for record in records if record['type'] == rtype ]
        if name:
            cmp_name = self._relative_name(name.lower())
            records = [ record for record in records if record['name'] == cmp_name ]
        if content:
            records = [ record for record in records if record['value'] == content ]

        records = [ self._parse_response_record(record) for record in records ]

        LOGGER.debug('list_records: %s', records)

        return records

    def _parse_response_record(self, response_record):
        # Most fields in a record response match, except for content which is
        # value
        return {
            'content': response_record['value'],
            'name': response_record['name'],
            'ttl': response_record['ttl'],
            'type': response_record['type']
        }

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        None

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        None

    def _request(self, action='GET', url='/', data={}, query_params={}):
        if query_params is None:
            query_params = {}

        query_params['domain'] = self.domain
        query_params['json'] = 'yes'

        response = requests.request(
            action, self.endpoint + '/CMD_API_DNS_CONTROL',
            auth=HTTPBasicAuth(
                self._get_provider_option('auth_username'),
                self._get_provider_option('auth_password')
            ),
            params=query_params
        )

        # If the request fails for any reason, throw an error
        response.raise_for_status()

        return response.json()
