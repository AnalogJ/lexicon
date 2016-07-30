# -*- coding: utf-8 -*-
from base import Provider as BaseProvider
import requests
import json

def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify api id used to authenticate")
    subparser.add_argument("--auth-token", help="specify token used authenticate to DNS provider")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://dnsapi.cn'

    def authenticate(self):

        payload = self._post('/Domain.Info', {'domain':self.options['domain']})

        if payload['status']['code'] != '1':
            raise StandardError(payload['status']['message'])

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
            raise StandardError(payload['status']['message'])

        print 'create_record: {0}'.format(payload['status']['code'] == '1')
        return payload['status']['code'] == '1'

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._post('/Record.List', {'domain':self.options['domain']})
        print payload
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

        print 'list_records: {0}'.format(records)
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
        print data
        payload = self._post('/Record.Modify', data)
        print payload
        if payload['status']['code'] != '1':
            raise StandardError(payload['status']['message'])

        print 'update_record: {0}'.format(True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            print records
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise StandardError('Record identifier could not be found.')
        payload = self._post('/Record.Remove', {'domain_id': self.domain_id, 'record_id': identifier})

        if payload['status']['code'] != '1':
            raise StandardError(payload['status']['message'])

        # is always True at this point, if a non 200 response is returned an error is raised.
        print 'delete_record: {0}'.format(True)
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
