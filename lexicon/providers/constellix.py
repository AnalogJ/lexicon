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
    subparser.add_argument("--auth-username", help="specify the API key username used to authenticate")
    subparser.add_argument("--auth-token", help="specify secret key used authenticate=")

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
                self.domain_details = domain
                continue

        if not self.domain_id:
            raise Exception('No domain found')


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'name': self._relative_name(name),
            'ttl': self.options['ttl'],
            'roundRobin':
                [{'disableFlag': False,
                 'value': content}],
        }
        payload = {}
        try:
            payload = self._post('/domains/{0}/records/{1}/'.format(self.domain_id, type), record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 400:
                raise

                # http 400 is ok here, because the record probably already exists
        logger.debug('create_record: %s', 'name' in payload)
        return True


    # Currently returns the first value for hosts where there may be multiple
    # values.  Need to check to see how this is handled for other providers.
    def list_records(self, type=None, name=None, content=None):
        self._check_type(type)

        # Oddly, Constellix supports API-level filtering for everything except LOC
        # records, so we need to retrieve all records for LOC and filter based on type
        # on our end.
        if not type or type == 'LOC':
            payload = self._get('/domains/{0}/records/'.format(self.domain_id))
        else:
            payload = self._get('/domains/{0}/records/{1}/'.format(self.domain_id, type))

        records = []

        for record in payload:
            for rr in record['roundRobin']:
                processed_record = {
                    'type': record['type'],
                    'name': '{0}.{1}'.format(record['name'], self.options['domain']),
                    'ttl': record['ttl'],
                    'content': rr['value'],
                    'id': record['id']
                    }

                processed_record = self._clean_TXT_record(processed_record)
                records.append(processed_record)

        records = self._filter_records(records, type=type, name=name, content=content)

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        self._check_type(type)

        if not identifier:
            existing = self._guess_record(type, name)
            identifier = existing['id']

        if not identifier:
            raise Exception("No identifier provided")

        data = {
            'id': identifier,
            'ttl': self.options['ttl']
        }

        if content:
            data['value'] = content

        payload = self._put('/domains/{0}/records/{1}/{2}/'.format(self.domain_id, type, identifier), data)

        logger.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        self._check_type(type)

        delete_record_id = []
        if not identifier:
            records = self.list_records(type, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)
        
        logger.debug('delete_records: %s', delete_record_id)
        
        for record_id in delete_record_id:
            payload = self._delete('/domains/{0}/records/{1}/{2}/'.format(self.domain_id, type, record_id))

        # is always True at this point, if a non 200 response is returned an error is raised.
        logger.debug('delete_record: %s', True)
        return True

    # Helpers
    def _check_type(self, type=None):
        # Constellix doesn't treat SOA as a separate record type, so we bail on SOA modificiations.
        # It looks like it would be possible to fake SOA CRUD, so an area for possible future
        # improvement

        if type == 'SOA':
            raise Exception('{0} record type is not supported in the Constellix Provider'.format(type))

        return True


    def _filter_records(self, records, type=None, name=None, content=None):
        _records = []
        for record in records:
            if (not type or record['type'] == type) and \
               (not name or record['name'] == self._full_name(name)) and \
               (not content or record['content'] == content):
                _records.append(record)
        return _records

    def _guess_record(self, type, name=None, content=None):
        records = self.list_records(type=type, name=name, content=content)
        if len(records) == 1:
            return records[0]
        elif len(records) > 1:
            raise Exception('Identifier was not provided and several existing records match the request for {0}/{1}'.format(type,name))
        elif len(records) == 0:
            raise Exception('Identifier was not provided and no existing records match the request for {0}/{1}'.format(type,name))    

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'x-cnsdns-apiKey': self.options['auth_username'],
        }
        default_auth = None

        # Date string in epoch format
        request_date = str(int(time.time() * 1000))

        hashed = hmac.new(self.options['auth_token'], msg=request_date, digestmod=sha1)

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
