'''Module provider for EUserv'''
from __future__ import absolute_import

import json
import logging
import requests

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['euserv.com']

# Success response code
RC_SUCCESS = 100

API_ENDPOINT = 'https://support.euserv.com/'

# Product group ID for domains
PRODUCT_ID_DOMAIN = 1


def provider_parser(subparser):
    '''Configure provider parser for Euserv'''
    subparser.add_argument(
        '--auth-username', help='specify email address for authentication')
    subparser.add_argument(
        '--auth-password', help='specify password for authentication')


class Provider(BaseProvider):
    '''Provider class for Euserv'''
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = API_ENDPOINT
        # Order ID for the domain
        self.order_id = None
        self.domain_id = None
        self.session_id = None

    def _authenticate(self):
        if not (self._get_provider_option('auth_username')
                and self._get_provider_option('auth_password')):
            raise Exception('username and password must be specified, add --help for details')

        # Get a session ID first.
        response = self._get()
        self.session_id = response['result']['sess_id']['value']

        auth_response = self._get('login', {
            'email': self._get_provider_option('auth_username'),
            'password': self._get_provider_option('auth_password')
            })

        # Find the contract number of the given domain
        orders = auth_response['result']['orders']

        for order in orders:
            if int(order['pg_id']['value']) == PRODUCT_ID_DOMAIN:
                # The description contains the description of the product itself
                # and in a second line the domain name
                order_description = order['ord_description']['value'].split('\n')

                if order_description[1] == self.domain:
                    self.order_id = order['ord_no']['value']
                    break

        if self.order_id is None:
            raise Exception('Order for domain not found')

        # Select the order for the given domain so we can use the DNS actions
        self._get('choose_order', {
                'ord_no': self.order_id
            })

        # Retrieve domain ID
        domains = self._get('kc2_domain_dns_get_records')

        for domain in domains['result']['domains']:
            if domain['dom_domain']['value'] == self.domain:
                self.domain_id = domain['dom_id']['value']
                break

        if self.domain_id is None:
            raise Exception('Domain not found in DNS records')

    def _create_record(self, rtype, name, content):
        pass

    def _list_records(self, rtype=None, name=None, content=None):
        pass

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        pass

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        pass

    # Helpers
    # url param used as subaction
    def _request(self, action='GET', url=None, data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        query_params['method'] = 'json';

        if self.session_id is not None:
            query_params['sess_id'] = self.session_id

        if url is not None:
            query_params['subaction'] = url

        response = requests.request(action, self.api_endpoint, params=query_params,
                                    data=json.dumps(data),
                                    headers={'Content-Type': 'application/json; charset=utf-8'}
                                    )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()

        response_json = response.json()

        if int(response_json['code']) != RC_SUCCESS:
            raise Exception('Error {0} in request: {1}'.format(response_json['code'], response_json['message']))

        return response_json