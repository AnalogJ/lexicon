from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify email address used to authenticate")
    subparser.add_argument("--auth-token", help="specify token used authenticate")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://pointhq.com')

    def authenticate(self):

        payload = self._get('/zones/{0}'.format(self.options['domain']))

        if not payload['zone']:
            raise Exception('No domain found')

        self.domain_id = payload['zone']['id']

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        # check if record already exists
        existing_records = self.list_records(type, name, content)
        if len(existing_records) == 1:
            return True

        payload = self._post('/zones/{0}/records'.format(self.domain_id), {'zone_record': {'record_type': type, 'name': self._relative_name(name), 'data': content}})

        logger.debug('create_record: %s', payload['zone_record'])
        return bool(payload['zone_record'])

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}
        if type:
            filter['record_type'] = type
        if name:
            filter['name'] = self._relative_name(name)

        payload = self._get('/zones/{0}/records'.format(self.domain_id), filter)

        records = []
        for record in payload:
            processed_record = {
                'type': record['zone_record']['record_type'],
                'name': self._full_name(record['zone_record']['name']),
                'ttl': record['zone_record']['ttl'],
                'content': record['zone_record']['data'],
                'id': record['zone_record']['id']
            }
            processed_record = self._clean_TXT_record(processed_record)
            records.append(processed_record)

        if content:
            records = [record for record in records if record['content'] == content]

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {}
        if type:
            data['record_type'] = type
        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['data'] = content

        payload = self._put('/zones/{0}/records/{1}'.format(self.domain_id, identifier), {'zone_record': data})

        logger.debug('update_record: %s', payload)
        return bool(payload['zone_record'])

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self.list_records(type, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)
        
        logger.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            payload = self._delete('/zones/{0}/records/{1}'.format(self.domain_id, record_id))

        logger.debug('delete_record: %s', True)
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             auth=requests.auth.HTTPBasicAuth(self.options['auth_username'], self.options['auth_token']),
                             headers={
                                 'Content-Type': 'application/json',
                                 'Accept': 'application/json'
                             })
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
