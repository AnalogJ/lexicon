"""Rackspace provider implementation"""

from __future__ import absolute_import
from __future__ import print_function

import json
import logging
import time

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

def _async_request_completed(payload):
    """Looks into an async response payload to see if the requested job has finished."""
    if payload['status'] == 'COMPLETED':
        return True
    if payload['status'] == 'ERROR':
        return True
    return False

def ProviderParser(subparser):
    subparser.add_argument("--auth-account", help="specify account number used to authenticate")
    subparser.add_argument("--auth-username", help="specify username used to authenticate. Only used if --auth-token is empty.")
    subparser.add_argument("--auth-api-key", help="specify api key used to authenticate. Only used if --auth-token is empty.")
    subparser.add_argument("--auth-token", help="specify token used authenticate. If empty, the username and api key will be used to create a token.")
    subparser.add_argument("--sleep-time", type=float, default=1, help="number of seconds to wait between update requests.")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get(
            'api_endpoint',
            'https://dns.api.rackspacecloud.com/v1.0'
        )
        self.auth_api_endpoint = self.engine_overrides.get(
            'auth_api_endpoint',
            'https://identity.api.rackspacecloud.com/v2.0'
        )

    def authenticate(self):
        if not self.options['auth_token']:
            auth_response = self._auth_request('POST', '/tokens', {
                'auth': {
                    'RAX-KSKEY:apiKeyCredentials': {
                        'username': self.options['auth_username'],
                        'apiKey': self.options['auth_api_key']
                    }
                }
            })
            self.options['auth_token'] = auth_response['access']['token']['id']

        payload = self._get('/domains', {
            'name': self.options['domain']
        })

        if not payload['domains']:
            raise Exception('No domain found')
        if len(payload['domains']) > 1:
            raise Exception('Too many domains found. This should not happen')

        self.domain_id = payload['domains'][0]['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        data = {'records': [{'type': type, 'name': self._full_name(name), 'data': content}]}
        if self.options.get('ttl'):
            data['records'][0]['ttl'] = self.options.get('ttl')

        try:
            payload = self._post_and_wait('/domains/{0}/records'.format(self.domain_id), data)
        except Exception as e:
            if str(e).startswith('Record is a duplicate of another record'):
                return self.update_record(None, type, name, content)
            raise e

        success = len(payload['records']) > 0
        logger.debug('create_record: %s', success)
        return success

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        params = {'per_page': 100}
        if type:
            params['type'] = type
        if name:
            params['name'] = self._full_name(name)
        # Sending the data filter to the Rackspace DNS API results in a 503 error
        # if content:
        #     params['data'] = content

        payload = self._get('/domains/{0}/records'.format(self.domain_id), params)

        records = list(payload['records'])
        if content:
            records = [record for record in records if record['data'] == content]
        records = [{
            'type': record['type'],
            'name': record['name'],
            'ttl': record['ttl'],
            'content': record['data'],
            'id': record['id']
        } for record in records]

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        data = {}
        if type:
            data['type'] = type
        if name:
            data['name'] = self._full_name(name)
        if content:
            data['data'] = content
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')

        if identifier is None:
            records = self.list_records(type, name)
            if len(records) < 1:
                raise Exception('Unable to find record to modify: ' + name)
            identifier = records[0]['id']

        self._put_and_wait('/domains/{0}/records/{1}'.format(self.domain_id, identifier), data)

        # If it didn't raise from the http status code, then we're good
        logger.debug('update_record: %s', identifier)
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
            payload = self._delete_and_wait(
                '/domains/{0}/records/{1}'.format(self.domain_id, record_id)
            )

        # If it didn't raise from the http status code, then we're good
        success = True
        logger.debug('delete_record: %s', success)
        return success


    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        full_url = (self.api_endpoint + '/{0}' + url).format(self.options.get('auth_account'))
        r = requests.request(action, full_url, params=query_params,
                             data=json.dumps(data),
                             headers={
                                 'X-Auth-Token': self.options.get('auth_token'),
                                 'Content-Type': 'application/json'
                             })
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()

    # Non-GET requests to the Rackspace CloudDNS API are asynchronous
    def _request_and_wait(self, action='POST', url='/', data=None, query_params=None):
        result = self._request(action, url, data, query_params)

        sleep_time = self.options.get('sleep_time')
        if sleep_time == "":
            sleep_time = "1"
        sleep_time = float(sleep_time)

        while not _async_request_completed(result):
            if sleep_time:
                time.sleep(sleep_time)
            result = self._update_response(result)

        if result['status'] == 'ERROR':
            raise Exception(result['error']['details'])

        if 'response' in result:
            return result['response']
        return None

    def _post_and_wait(self, url='/', data=None, query_params=None):
        return self._request_and_wait('POST', url, data, query_params)

    def _put_and_wait(self, url='/', data=None, query_params=None):
        return self._request_and_wait('PUT', url, data, query_params)

    def _delete_and_wait(self, url='/', data=None, query_params=None):
        return self._request_and_wait('DELETE', url, data, query_params)

    def _update_response(self, payload):
        r = requests.request('GET', payload['callbackUrl'], params={'showDetails': 'true'},
                             data={},
                             headers={
                                 'X-Auth-Token': self.options.get('auth_token'),
                                 'Content-Type': 'application/json'
                             })

        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()

    def _auth_request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}

        r = requests.request(action, self.auth_api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers={
                                 'Content-Type': 'application/json'
                             })
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
