# The Constellix API has some limitations.  We try to paper over them here, but here's what you need to be
# aware of:
#
#  1) SOA records are not first-class record types in the Constellix API, so are not supported.
#  2) We expect all records to use the "Standard" record type, so failover, pools or round robin with
#     failover are not supported.
#  3) Because Constellix represents record sets as a single record with multiple values attached, not as 
#     a set of separate records, create and delete operations end up becoming read/update operations when
#     working with record sets.
#
#     Since these aren't atomic operations, it creates a small window where you could have data loss
#     if multiple processes were trying to work with the same record set.
#
#     This is unlikely to be a problem in most scenarios, but the possilbity is there.  I've reached
#     out to the Constellix folks to see if they have plans to clean up the API to resolve this.

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
            # If there is already a record with that name, we need to do an update.
            if e.response.status_code == 400:
                existing_records = self.list_records(type=type, name=name)
                new_content = [r['content'] for r in existing_records]

                # Only do the update if we are creating a record that doesn't already exist, otherwise
                # Constellix will throw an error.
                if content not in new_content:
                    new_content.append(content)
                    self.update_record(existing_records[0]['id'], type=type, name=name, content=new_content)
            else:
                raise
        logger.debug('create_record: %s', 'name' in payload)
        return True


    # Currently returns the first value for hosts where there may be multiple
    # values.  Need to check to see how this is handled for other providers.
    def list_records(self, type=None, name=None, content=None, identifier=None):
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

        records = self._filter_records(records, type=type, name=name, content=content, identifier=identifier)

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        self._check_type(type)

        if content and not isinstance(content, (list)):
            content = [content]

        if identifier and (not type or not name):
            record = self.list_records(identifier=identifier)
            type = record[0]['type']
            name = record[0]['name']
        elif not identifier:
            record = self.list_records(type, name)
            identifier = record[0]['id']

        if not identifier:
            raise Exception("No identifier provided")

        data = {
            'id': identifier,
            'ttl': self.options['ttl'],
            'name': self._relative_name(name)
        }

        data['roundRobin'] = []

        for c in content:
            data['roundRobin'].append({'disableFlag': False,
                                       'value': c})

        payload = self._put('/domains/{0}/records/{1}/{2}/'.format(self.domain_id, type, identifier), data)

        logger.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        self._check_type(type)

        records = self.list_records(identifier=identifier, type=type, name=name)

        # If we are filtering delete records by content and we are going to have
        # at least one record left over after deleting, then this becomes an
        # update operation.
        if content:
            current_content = set(r['content'] for r in records)
            if content in current_content and len(current_content) > 1:
                current_content.remove(content)
                self.update_record(records[0]['id'], type=type, name=name, content=list(current_content))
                return True

        delete_record_id = set(record['id'] for record in records)

        # We need a type to do a delete, so pull one from the first record if it's not supplied.
        if not type:
            type = records[0]['type']
        
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


    def _filter_records(self, records, type=None, name=None, content=None, identifier=None):
        _records = []
        for record in records:
            if (not identifier or record['id'] == identifier) and \
               (not type or record['type'] == type) and \
               (not name or record['name'] == self._full_name(name)) and \
               (not content or record['content'] == content):
                _records.append(record)
        return _records

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
