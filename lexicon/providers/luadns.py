"""Module provider for luadns"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['luadns.com']


def provider_parser(subparser):
    """Configure provider parser for luadns"""
    subparser.add_argument(
        "--auth-username", help="specify email address for authentication")
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")


class Provider(BaseProvider):
    """Provider class for luadns"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.luadns.com/v1'

    def _authenticate(self):
        payload = self._get('/zones')

        domain_info = next(
            (domain for domain in payload if domain['name'] == self.domain), None)

        if not domain_info:
            raise Exception('No domain found')

        self.domain_id = domain_info['id']

    # Create record. If record already exists with the same content, do nothing'

    def _create_record(self, rtype, name, content):
        # check if record already exists
        existing_records = self._list_records(rtype, name, content)
        if len(existing_records) == 1:
            return True

        self._post('/zones/{0}/records'.format(self.domain_id),
                   {'type': rtype,
                    'name': self._fqdn_name(name),
                    'content': content,
                    'ttl': self._get_lexicon_option('ttl')})

        LOGGER.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get('/zones/{0}/records'.format(self.domain_id))

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': self._full_name(record['name']),
                'ttl': record['ttl'],
                'content': record['content'],
                'id': record['id']
            }
            records.append(processed_record)

        if rtype:
            records = [record for record in records if record['type'] == rtype]
        if name:
            records = [record for record in records if record['name']
                       == self._full_name(name)]
        if content:
            records = [
                record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        data = {
            'ttl': self._get_lexicon_option('ttl')
        }
        if rtype:
            data['type'] = rtype
        if name:
            data['name'] = self._fqdn_name(name)
        if content:
            data['content'] = content

        self._put(
            '/zones/{0}/records/{1}'.format(self.domain_id, identifier), data)

        LOGGER.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            self._delete(
                '/zones/{0}/records/{1}'.format(self.domain_id, record_id))

        LOGGER.debug('delete_record: %s', True)
        return True

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = requests.request(action, self.api_endpoint + url, params=query_params,
                                    data=json.dumps(data),
                                    auth=requests.auth.HTTPBasicAuth(self._get_provider_option(
                                        'auth_username'), self._get_provider_option('auth_token')),
                                    headers={
                                        'Content-Type': 'application/json',
                                        'Accept': 'application/json'
                                    })
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()
