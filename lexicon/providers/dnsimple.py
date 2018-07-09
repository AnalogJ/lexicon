from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify api token used to authenticate")
    subparser.add_argument("--auth-username", help="specify email address used to authenticate")
    subparser.add_argument("--auth-password", help="specify password used to authenticate")
    subparser.add_argument("--auth-2fa", help="specify two-factor auth token (OTP) to use with email/password authentication")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.account_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.dnsimple.com/v2')

    def authenticate(self):

        payload = self._get('/accounts')

        if not payload[0]['id']:
            raise Exception('No account id found')

        for account in payload:
            dompayload = self._get('/{0}/domains'.format(account['id']), query_params={'name_like': self.options.get('domain')})
            if len(dompayload) > 0 and dompayload[0]['id']:
                self.account_id = account['id']
                self.domain_id = dompayload[0]['id']

        if not self.account_id:
            raise Exception('No domain found like {}'.format(self.options.get('domain')))


    # Create record. If record already exists with the same content, do nothing
    def create_record(self, type, name, content):
        # check if record already exists
        existing_records = self.list_records(type, name, content)
        if len(existing_records) == 1:
            return True

        record = {
            'type': type,
            'name': self._relative_name(name),
            'content': content
        }
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')
        if self.options.get('priority'):
            record['priority'] = self.options.get('priority')
        if self.options.get('regions'):
            record['regions'] = self.options.get('regions')

        payload = self._post('{0}/zones/{1}/records'.format(self.account_id, self.options.get('domain')), record)

        logger.debug('create_record: %s', 'id' in payload)
        return 'id' in payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}
        if type:
            filter['type'] = type
        if name:
            filter['name'] = self._relative_name(name)
        payload = self._get('/{0}/zones/{1}/records'.format(self.account_id, self.options.get('domain')), query_params=filter)

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': '{}'.format(self.options.get('domain')) if record['name'] == "" else '{0}.{1}'.format(record['name'],self.options.get('domain')),
                'ttl': record['ttl'],
                'content': record['content'],
                'id': record['id']
            }
            if record['priority']:
                processed_record['priority'] = record['priority']
            records.append(processed_record)

        if content:
            records = [record for record in records if record['content'] == content]

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {}

        if identifier == None:
            records = self.list_records(type, name, content)
            identifiers = [record["id"] for record in records]
        else:
            identifiers = [identifier]

        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['content'] = content
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')
        if self.options.get('priority'):
            data['priority'] = self.options.get('priority')
        if self.options.get('regions'):
            data['regions'] = self.options.get('regions')

        for identifier in identifiers:
            payload = self._patch('/{0}/zones/{1}/records/{2}'.format(self.account_id, self.options.get('domain'), identifier), data)
            logger.debug('update_record: %s', identifier)

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
            payload = self._delete('/{0}/zones/{1}/records/{2}'.format(self.account_id, self.options.get('domain'), record_id))

        # is always True at this point; if a non 2xx response is returned, an error is raised.
        logger.debug('delete_record: True')
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        default_auth = None

        if self.options.get('auth_token'):
            default_headers['Authorization'] = "Bearer {0}".format(self.options.get('auth_token'))
        elif self.options.get('auth_username') and self.options.get('auth_password'):
            default_auth = (self.options.get('auth_username'),self.options.get('auth_password'))
            if self.options.get('auth_2fa'):
                default_headers['X-Dnsimple-OTP'] = self.options.get('auth_2fa')
        else:
            raise Exception('No valid authentication mechanism found')

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        if r.text and r.json()['data'] == None:
            raise Exception('No data returned')

        return r.json()['data'] if r.text else None

    def _patch(self, url='/', data=None, query_params=None):
        return self._request('PATCH', url, data=data, query_params=query_params)
