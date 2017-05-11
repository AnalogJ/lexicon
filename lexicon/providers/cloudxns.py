# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function
from future.standard_library import install_aliases
install_aliases()

import hashlib
import json
import logging
import time

import requests

from .base import Provider as BaseProvider

from urllib.parse import urlencode

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify API-KEY used authenticate to DNS provider")
    subparser.add_argument("--auth-token", help="specify SECRET-KEY used authenticate to DNS provider")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://www.cloudxns.net/api2')

    def authenticate(self):

        payload = self._get('/domain')
        for record in payload['data']:
            if record['domain'] == self.options['domain']+'.':
                self.domain_id = record['id']
                break

        if self.domain_id == None:
            raise Exception('No domain found')

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):

        record = {
            'domain_id': self.domain_id,
            'host': self._relative_name(name),
            'value': content,
            'type': type,
            'line_id': 1,
        }
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')

        payload = self._post('/record', record)

        logger.debug('create_record: %s', True) # CloudXNS will return bad HTTP Status when error, will throw at r.raise_for_status() in _request()
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._get('/record/' + self.domain_id, {'host_id':0, 'offset':0, 'row_num': 2000})
        records = []
        for record in payload['data']:
            processed_record = {
                'type': record['type'],
                'name': self._full_name(record['host']),
                'ttl': record['ttl'],
                'content': record['value'],
                #this id is useless unless your doing record linking. Lets return the original record identifier.
                'id': record['record_id'] #
            }
            if processed_record['type'] == 'TXT':
                processed_record['content'] = processed_record['content'].replace('"', '')
                # CloudXNS will add quotes automaticly for TXT records, https://www.cloudxns.net/Support/detail/id/114.html
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

        if not identifier:
            records = self.list_records(name=name)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')

        data = {
            'domain_id': self.domain_id,
            'host': self._relative_name(name),
            'value': content,
            'type': type
        }
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')

        payload = self._put('/record/' + identifier, data)

        logger.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):

        if not identifier:
            records = self.list_records(type, name, content)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')

        payload = self._delete('/record/' + identifier + '/' + self.domain_id)

        # is always True at this point, if a non 200 response is returned an error is raised.
        logger.debug('delete_record: %s', True)
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        data['login_token'] = self.options['auth_username'] + ',' + self.options['auth_token']
        data['format'] = 'json'
        if query_params:
            query_string = '?' + urlencode(query_params)
        else:
            query_string = ''
            query_params = {}
        if data:
            data = json.dumps(data)
        else:
            data = ''
        date = time.strftime('%a %b %d %H:%M:%S %Y', time.localtime())
        default_headers = {
            'API-KEY': self.options['auth_username'],
            'API-REQUEST-DATE': date,
            'API-HMAC': hashlib.md5("{0}{1}{2}{3}{4}{5}{6}".format(self.options['auth_username'],self.api_endpoint, url, query_string, data, date, self.options['auth_token']).encode('utf-8')).hexdigest(),
            'API-FORMAT':'json'
        }
        default_auth = None
        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=data,
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
