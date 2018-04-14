from __future__ import absolute_import
from __future__ import print_function

import base64
import contextlib
import hmac
import json
import locale
import logging
import time
from hashlib import sha1

import requests
from builtins import bytes

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.add_argument("--auth-api-key", help="specify the API key username used to authenticate")
    subparser.add_argument("--auth-secret", help="specify secret key used authenticate=")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.dns.constellix.com/v1')

    def authenticate(self):
        try:
            payload = self._get('/domains/')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                payload = {}
            else:
                raise e
    
        for domain in payload:
            if domain['name'] == self.options['domain']:
                self.domain_id = domain['id']
                continue

        if not self.domain_id:
            raise Exception('No domain found')


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'type': type,
            'name': self._relative_name(name),
            'value': content,
            'ttl': self.options['ttl']
        }
        payload = {}
        try:
            payload = self._post('/dns/managed/{0}/records/'.format(self.domain_id), record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 400:
                raise

                # http 400 is ok here, because the record probably already exists
        logger.debug('create_record: %s', 'name' in payload)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}
        if type:
            filter['type'] = type
        if name:
            filter['recordName'] = self._relative_name(name)
        payload = self._get('/domains/{0}/records/{1}/'.format(self.domain_id, type))

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': '{0}.{1}'.format(record['name'], self.options['domain']),
                'ttl': record['ttl'],
                'content': record['value'],
                'id': record['id']
            }

            processed_record = self._clean_TXT_record(processed_record)
            records.append(processed_record)

        if content:
            records = [record for record in records if record['content'].lower() == content.lower()]

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'id': identifier,
            'ttl': self.options['ttl']
        }

        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['value'] = content
        if type:
            data['type'] = type

        payload = self._put('/dns/managed/{0}/records/{1}'.format(self.domain_id, identifier), data)

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
            payload = self._delete('/dns/managed/{0}/records/{1}'.format(self.domain_id, record_id))

        # is always True at this point, if a non 200 response is returned an error is raised.
        logger.debug('delete_record: %s', True)
        return True


    # Helpers

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'x-cnsdns-apiKey': self.options['auth_api_key'],
        }
        default_auth = None

        # Date string in epoch format
        request_date = str(int(time.time() * 1000))

        hashed = hmac.new(self.options['auth_secret'], msg=request_date, digestmod=sha1)

        default_headers['x-cnsdns-requestDate'] = request_date
        default_headers['x-cnsdns-hmac'] = base64.b64encode(hashed.digest())

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.

        # PUT and DELETE actions dont return valid json.
        if action == 'DELETE' or action == 'PUT':
            return r.text
        return r.json()
