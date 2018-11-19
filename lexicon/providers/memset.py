from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['memset.com']


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-token", help="specify API key for authentication")


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.memset.com/v1/json'

    def authenticate(self):
        payload = self._get('/dns.zone_domain_info', {
            'domain': self.domain
        })
        if not payload['zone_id']:
            raise Exception('No domain found')
        self.domain_id = payload['zone_id']

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        data = {'type': type, 'record': self._relative_name(
            name), 'address': content}
        if self._get_lexicon_option('ttl'):
            data['ttl'] = self._get_lexicon_option('ttl')
        data['zone_id'] = self.domain_id
        check_exists = self.list_records(type=type, name=name, content=content)
        if not len(check_exists) > 0:
            payload = self._get('/dns.zone_record_create', data)
            if payload['id']:
                self._get('/dns.reload')
                LOGGER.debug('create_record: %s', payload['id'])
                return payload['id']
        else:
            return check_exists

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        payload = self._get('/dns.zone_info', {
            'id': self.domain_id
        })
        records = []
        for record in payload['records']:
            processed_record = {
                'type': record['type'],
                'name': self._full_name(record['record']),
                'ttl': record['ttl'],
                'content': record['address'],
                'id': record['id']
            }
            if name:
                name = self._full_name(name)
            if (processed_record['type'] == type):
                if (name is not None and content is not None):
                    if processed_record['name'] == name and processed_record['content'] == content:
                        records.append(processed_record)
                elif (name is not None and content is None):
                    if processed_record['name'] == name:
                        records.append(processed_record)
                elif (name is None and content is not None):
                    if processed_record['content'] == content:
                        records.append(processed_record)
                else:
                    records.append(processed_record)

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        data = {}
        if not identifier:
            records = self.list_records(type, self._relative_name(name))
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')
        if type:
            data['type'] = type
        if name:
            data['record'] = self._relative_name(name)
        if content:
            data['address'] = content
        if self._get_lexicon_option('ttl'):
            data['ttl'] = self._get_lexicon_option('ttl')
        data['id'] = identifier
        data['zone_id'] = self.domain_id

        payload = self._get('/dns.zone_record_update', data)
        if payload['id']:
            self._get('/dns.reload')
            LOGGER.debug('update_record: %s', payload['id'])
            return payload['id']

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self.list_records(
                type, self._relative_name(name), content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            payload = self._get('/dns.zone_record_delete', {'id': record_id})

        if len(record_id) > 0:
            self._get('/dns.reload')

        LOGGER.debug('delete_record: %s', True)
        return True

    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             auth=(self._get_provider_option(
                                 'auth_token'), 'x'),
                             headers={'Content-Type': 'application/json'})
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        return r.json()
