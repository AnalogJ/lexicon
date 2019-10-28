"""Module provider for Dynu.com"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dynu.com']


def provider_parser(subparser):
    """Module provider for Dynu.com"""
    subparser.add_argument(
        "--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):
    """Provider class for Dynu.com"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.dynu.com/v2'

    def _authenticate(self):
        pass

    # Create record. If record already exists with the same content, do nothing.
    def _create_record(self, rtype, name, content):
        pass

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        pass

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        pass

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        pass

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        # Dynu API does not respond to query parameters at all, so we ignore them
        response = requests.request(action, self.api_endpoint + url, data=json.dumps(data),
                                    headers={
                                        'API-Key': self._get_provider_option('auth_token'),
                                        'Accept': 'application/json',
                                        'Content-Type': 'application/json'
                                    })
        response.raise_for_status()
        return response.json()