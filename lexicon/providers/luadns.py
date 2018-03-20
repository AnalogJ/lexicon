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
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.luadns.com/v1')

    def authenticate(self):

        payload = self._get('/zones')

        domain_info = next((domain for domain in payload if domain['name'] == self.options['domain']), None)

        if not domain_info:
            raise Exception('No domain found')

        self.domain_id = domain_info['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        # check if record already exists
        existing_records = self.list_records(type, name, content)
        if len(existing_records) == 1:
            return True

        payload = self._post('/zones/{0}/records'.format(self.domain_id), {'type': type, 'name': self._fqdn_name(name), 'content': content, 'ttl': self.options['ttl']})

        logger.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
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

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'] == content]

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'ttl': self.options['ttl']
        }
        if type:
            data['type'] = type
        if name:
            data['name'] = self._fqdn_name(name)
        if content:
            data['content'] = content


        payload = self._put('/zones/{0}/records/{1}'.format(self.domain_id, identifier), data)

        logger.debug('update_record: %s', True)
        return True

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
