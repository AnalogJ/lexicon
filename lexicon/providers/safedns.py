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
    subparser.add_argument('--auth-token', help='specify the API key to authenticate with')

class Provider(BaseProvider):
    """
    //todo comment here
    """
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.ukfast.io/safedns/v1'

    def _authenticate(self):
        self._get('/zones/{0}'.format(self.domain))
        self.domain_id = self.domain

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    def _list_records(self, rtype=None, name=None, content=None):
        url = '/zones/{0}/records'.format(self.domain_id)
        records = []
        payload = {}

        # Handle pagination and iteratively collect all records
        next_url = url
        while next_url is not None:
            payload = self._get(next_url)
            if 'meta' in payload \
                    and 'pagination' in payload['meta'] \
                    and 'links' in payload['meta']['pagination'] \
                    and 'next' in payload['meta']['pagination']['links']:
                next_url = payload['meta']['pagination']['links']['next']
            else:
                next_url = None

            # Assign the returned attributes to the keys that lexicon expects
            for record in payload['data']:
                processed_record = {
                    'id': record['id'],
                    'name': record['name'],
                    'type': record['type'],
                    'content': record['content'],
                    'updated_at': record['updated_at'],
                    'ttl': record['ttl'],
                    'priority': record['priority']
                }
                records.append(processed_record)

        # This appears to be filtering logic to return only the record
        # which matches what's passed in to the method
        if rtype:
            records = [
                record for record in records
                if record['type'] == rtype]
        if name:
            records = [
                record for record in records
                # DNS should not be case-sensitive, so perform lower-case comparison
                if record['name'].lower() == self._full_name(name).lower()]
        if content:
            records = [
                record for record in records
                if record['content'].lower() == content.lower()]

        LOGGER.debug('list_records: %s', records)
        return records

    def _create_record(self, rtype, name, content):

        # We ignore creation if a record already exists for given rtype/name/content
        records = self._list_records(rtype, name, content)
        if records:
            LOGGER.debug('create_record (ignored, duplicate): %s',
                         records[0]['id'])
            return True

        data = {
            'name': self._full_name(name),
            'type': rtype,
            'content': content
        }

        try:
            result = self._post('/zones/{0}/records'.format(self.domain), data)
        except requests.exceptions.HTTPError as err:
            # LOGGER.debug('Error occurred: ', err)
            raise

        if not result['content']:
            raise Exception('Error occured when inserting the new record.')

        LOGGER.debug('create_record: %s', True)
        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        ''''''

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        ''''''

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': '{0}'.format(self._get_provider_option('auth_token'))
        }
        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        response = requests.request(action, url, params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers)
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if action == 'DELETE':
            return ''
        return response.json()
