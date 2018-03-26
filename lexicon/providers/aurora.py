from __future__ import absolute_import
from __future__ import print_function

import json
import logging
import base64
import hmac
import hashlib
import datetime

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.add_argument("--auth-api-key", help="specify API key to authenticate")
    subparser.add_argument("--auth-secret-key", help="specify the secret key to authenticate")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.auroradns.eu')

    def authenticate(self):
        zone = None
        payload = self._get('/zones')

        for item in payload:
            if item['name'] == self.options['domain']:
                zone = item

        if not zone:
            raise Exception('No domain found')

        self.domain_id = zone['id']

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        data = {'type': type, 'name': self._relative_name(name), 'content': content}
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')
        payload = self._post('/zones/{0}/records'.format(self.domain_id), data)

        logger.debug('create_record: {0}'.format(payload))
        return payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        payload = self._get('/zones/{0}/records'.format(self.domain_id))

        # Apply filtering first.
        processed_records = payload
        if type:
            processed_records = [record for record in processed_records if record['type'] == type]
        if name:
            processed_records = [record for record in processed_records if record['name'] == self._relative_name(name)]
        if content:
            processed_records = [record for record in processed_records if record['content'].lower() == content.lower()]

        # Format the records.
        records = []
        for record in processed_records:
            processed_record = {
                'type': record['type'],
                'name': self._full_name(record['name']),
                'ttl': record['ttl'],
                'content': record['content'],
                'id': record['id']
            }
            records.append(processed_record)

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        # Try to find record if no identifier was specified
        if not identifier:
            identifier = self._find_record_identifier(type, name, None)

        data = {}
        if type:
            data['type'] = type
        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['content'] = content
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')

        payload = self._put('/zones/{0}/records/{1}'.format(self.domain_id, identifier), data)

        logger.debug('update_record: %s', payload)
        return payload

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        # Try to find record if no identifier was specified
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
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        t = datetime.datetime.utcnow()
        timestamp = t.strftime('%Y%m%dT%H%M%SZ')
        authorization_header = self._generate_auth_header(action, url, timestamp)

        r = requests.request(action, self.api_endpoint + url, params=query_params,
            data=json.dumps(data),
            headers={
                'X-AuroraDNS-Date': timestamp,
                'Authorization': authorization_header,
                'Content-Type': 'application/json'
            })

        # If the response is a HTTP 409 statusCode, the record already exists: return true.
        if r.status_code == 409:
            return True

        # If the request fails for any other reason, throw an error.
        r.raise_for_status()

        # Try to parse the json, if it not exists, return true.
        try:
            return r.json()
        except:
            return True

    def _generate_auth_header(self, action, url, timestamp):
        secret_key = self.options['auth_secret_key']
        api_key = self.options['auth_api_key']
        sig = action + url + timestamp

        signature = base64.b64encode(hmac.new(
            secret_key.encode('utf-8'), sig.encode('utf-8'),
            digestmod=hashlib.sha256).digest())

        auth = api_key + ':' + signature.decode('utf-8')
        auth_b64 = base64.b64encode(auth.encode('utf-8'))
        return 'AuroraDNSv1 %s' % (auth_b64.decode('utf-8'))

    def _find_record_identifier(self, type, name, content):
        records = self.list_records(type, name, content)
        logger.debug('records: %s', records)
        if len(records) == 1:
            return records[0]['id']
        else:
            raise Exception('Record identifier could not be found. Try to provide an identifier')
