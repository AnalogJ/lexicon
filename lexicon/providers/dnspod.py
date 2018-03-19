# -*- coding: utf-8 -*-
from __future__ import absolute_import
from __future__ import print_function

import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify api id used to authenticate")
    subparser.add_argument("--auth-token", help="specify token used authenticate to DNS provider")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://dnsapi.cn')

    def authenticate(self):

        payload = self._post('/Domain.Info', {'domain':self.options['domain']})

        if payload['status']['code'] != '1':
            raise Exception(payload['status']['message'])

        self.domain_id = payload['domain']['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'domain_id': self.domain_id,
            'sub_domain': self._relative_name(name),
            'record_type': type,
            'record_line': '默认',
            'value': content
        }
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')

        payload = self._post('/Record.Create', record)

        if payload['status']['code'] not in ['1', '31']:
            raise Exception(payload['status']['message'])

        logger.debug('create_record: %s', payload['status']['code'] == '1')
        return payload['status']['code'] == '1'

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._post('/Record.List', {'domain':self.options['domain']})
        logger.debug('payload: %s', payload)
        records = []
        for record in payload['records']:
            processed_record = {
                'type': record['type'],
                'name': self._full_name(record['name']),
                'ttl': record['ttl'],
                'content': record['value'],
                #this id is useless unless your doing record linking. Lets return the original record identifier.
                'id': record['id'] #
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
            'domain_id': self.domain_id,
            'record_id': identifier,
            'sub_domain': self._relative_name(name),
            'record_type': type,
            'record_line': '默认',
            'value': content
        }
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')
        logger.debug('data: %s', data)
        payload = self._post('/Record.Modify', data)
        logger.debug('payload: %s', payload)
        if payload['status']['code'] != '1':
            raise Exception(payload['status']['message'])

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
            payload = self._post('/Record.Remove', {'domain_id': self.domain_id, 'record_id': record_id})

            #if payload['status']['code'] != '1':
            #    raise Exception(payload['status']['message'])

        # is always True at this point, if a non 200 response is returned an error is raised.
        logger.debug('delete_record: %s', True)
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        data['login_token'] = self.options['auth_username'] + ',' + self.options['auth_token']
        data['format'] = 'json'
        if query_params is None:
            query_params = {}
        default_headers = {}
        default_auth = None
        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=data,
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
