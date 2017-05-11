from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify API key used to authenticate")


class Provider(BaseProvider):
    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.memset.com/v1/json')

    def authenticate(self):
        payload = self._get('/dns.zone_domain_info', {
            'domain': self.options['domain']
        })
        if not payload['zone_id']:
            raise Exception('No domain found')
        self.domain_id = payload['zone_id']

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        data = {'type': type, 'record': self._relative_name(name), 'address': content}
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')
        data['zone_id'] = self.domain_id
        check_exists = self.list_records(type=type, name=name, content=content)
        if not len(check_exists) > 0:
            payload = self._get('/dns.zone_record_create', data)
            if payload['id']:
                self._get('/dns.reload')
                logger.debug('create_record: %s', payload['id'])
                return payload['id']

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

        logger.debug('list_records: %s', records)
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
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')
        data['id'] = identifier
        data['zone_id'] = self.domain_id

        payload = self._get('/dns.zone_record_update', data)
        if payload['id']:
            self._get('/dns.reload')
            logger.debug('update_record: %s', payload['id'])
            return payload['id']

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, self._relative_name(name), content)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')
        payload = self._get('/dns.zone_record_delete', {'id': identifier})
        if payload['id']:
            self._get('/dns.reload')
            logger.debug('delete_record: %s', payload['id'])
            return payload['id']

    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             auth=(self.options['auth_token'], 'x'),
                             headers={'Content-Type': 'application/json'})
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
