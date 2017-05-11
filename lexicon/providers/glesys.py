from __future__ import absolute_import
from __future__ import print_function

import json

import requests

from .base import Provider as BaseProvider


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify username (CL12345)")
    subparser.add_argument("--auth-token", help="specify API key")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.glesys.com')

    def authenticate(self):
        payload = self._get('/domain/list')
        domains = payload['response']['domains']
        for record in domains:
            if record['domainname'] == self.options['domain']:
                # Domain records do not have any id.
                # Since domain_id cannot be None, use domain name as id instead.
                self.domain_id = record['domainname']
                break

        if self.domain_id == None:
            raise Exception('No domain found')

    # Create record. If record already exists with the same content, do nothing.
    def create_record(self, type, name, content):
        existing = self.list_records(type, name, content)
        if len(existing) > 0:
            # Already exists, do nothing.
            return True

        request_data = {
            'domainname': self.options['domain'],
            'host': self._full_name(name),
            'type': type,
            'data': content
        }
        self._addttl(request_data)

        self._post('/domain/addrecord', data=request_data)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        request_data = {
            'domainname': self.options['domain']
        }
        payload = self._post('/domain/listrecords', data=request_data)

        # Convert from Glesys record structure to Lexicon structure.
        processed_records = [self._glesysrecord2lexiconrecord(r) for r in payload['response']['records']]

        if type:
            processed_records = [record for record in processed_records if record['type'] == type]
        if name:
            processed_records = [record for record in processed_records if record['name'] == self._full_name(name)]
        if content:
            processed_records = [record for record in processed_records if record['content'].lower() == content.lower()]

        return processed_records

    # Update a record. Identifier must be specified.
    def update_record(self, identifier, type=None, name=None, content=None):
        request_data = {'recordid': identifier}
        if name:
            request_data['host'] = name
        if type:
            request_data['type'] = type
        if content:
            request_data['data'] = content

        self._addttl(request_data)
        self._post('/domain/updaterecord', data=request_data)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            if len(records) > 0:
                # At least one record was found. Delete first match.
                identifier = records[0]['id']

        if not identifier:
            # Does not exist, do nothing.
            return True

        request_data = {'recordid': identifier}
        self._post('/domain/deleterecord', data=request_data)
        return True

    # Helpers.
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        query_params['format'] = 'json'
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        credentials = (self.options['auth_username'], self.options['auth_token'])
        response = requests.request(action,
                                    self.api_endpoint + url,
                                    params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers,
                                    auth=credentials)

        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    # Adds TTL parameter if passed as argument to lexicon.
    def _addttl(self, request_data):
        if 'ttl'in self.options:
            request_data['ttl'] = self.options['ttl']

    # From Glesys record structure: [u'domainname', u'recordid', u'type', u'host', u'ttl', u'data']
    def _glesysrecord2lexiconrecord(self, glesys_record):
        return {
            'id': glesys_record['recordid'],
            'type': glesys_record['type'],
            'name': glesys_record['host'],
            'ttl': glesys_record['ttl'],
            'content': glesys_record['data']
        }
