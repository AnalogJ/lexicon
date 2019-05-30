"""Module provider for UKFast's SafeDNS"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['graphiterack.com']

def provider_parser(subparser):
    """Configure provider parser for SafeDNS"""
    subparser.description = '''
        SafeDNS Provider requires an API key to access its API.
        You can generate one for your account on the following URL:
        https://my.ukfast.co.uk/api/index.php'''
    subparser.add_argument('--api-key', help='specify your API key')

class Provider(BaseProvider):
    """
    //todo comment here
    """
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.zeit.co/v2/domains'

    def _authenticate(self):
        self._get_provider_option('api-key')
        
    def _list_records(self, rtype=None, name=None, content=None):
        self._get_provider_option('api-key')

    def _create_record(self, rtype, name, content):
        self._get_provider_option('api-key')

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        self._get_provider_option('api-key')

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        self._get_provider_option('api-key')

    def _request(self, action='GET', url='/', data=None, query_params=None):
        self._get_provider_option('api-key')
