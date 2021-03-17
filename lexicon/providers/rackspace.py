"""Rackspace provider implementation"""
from __future__ import absolute_import
import json
import logging
import time

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['rackspacecloud.com']


def _async_request_completed(payload):
    """Looks into an async response payload to see if the requested job has finished."""
    if payload['status'] == 'COMPLETED':
        return True
    if payload['status'] == 'ERROR':
        return True
    return False


def provider_parser(subparser):
    """Configure provider parser for Rackspace"""
    subparser.add_argument(
        "--auth-account", help="specify account number for authentication")
    subparser.add_argument(
        "--auth-username",
        help="specify username for authentication. Only used if --auth-token is empty.")
    subparser.add_argument(
        "--auth-api-key",
        help="specify api key for authentication. Only used if --auth-token is empty.")
    subparser.add_argument(
        "--auth-token",
        help=("specify token for authentication. "
              "If empty, the username and api key will be used to create a token."))
    subparser.add_argument("--sleep-time", type=float, default=1,
                           help="number of seconds to wait between update requests.")


class Provider(BaseProvider):
    """Provider class for Rackspace"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://dns.api.rackspacecloud.com/v1.0'
        self.auth_api_endpoint = 'https://identity.api.rackspacecloud.com/v2.0'
        self._auth_token = None
        self._auth_account = None

    def _get_rackspace_option(self, key):
        private_key = '_' + key
        result = None
        if hasattr(self, private_key):
            result = getattr(self, private_key)
        if result is None:
            result = self._get_provider_option(key)
        return result

    def _authenticate(self):
        self._auth_token = self._get_provider_option('auth_token')
        if not self._auth_token:
            auth_response = self._auth_request('POST', '/tokens', {
                'auth': {
                    'RAX-KSKEY:apiKeyCredentials': {
                        'username': self._get_provider_option('auth_username'),
                        'apiKey': self._get_provider_option('auth_api_key')
                    }
                }
            })
            self._auth_token = auth_response['access']['token']['id']
            self._auth_account = auth_response['access']['token']['tenant']['id']

        payload = self._get('/domains', {
            'name': self.domain
        })

        if not payload['domains']:
            raise Exception('No domain found')
        if len(payload['domains']) > 1:
            raise Exception('Too many domains found. This should not happen')

        self.domain_id = payload['domains'][0]['id']

    # Create record. If record already exists with the same content, do nothing'

    def _create_record(self, rtype, name, content):
        data = {'records': [
            {'type': rtype, 'name': self._full_name(name), 'data': content}]}
        if self._get_lexicon_option('ttl'):
            data['records'][0]['ttl'] = self._get_lexicon_option('ttl')

        try:
            payload = self._post_and_wait(
                '/domains/{0}/records'.format(self.domain_id), data)
        except Exception as error:
            if str(error).startswith('Record is a duplicate of another record'):
                return self._update_record(None, rtype, name, content)
            raise error

        success = len(payload['records']) > 0
        LOGGER.debug('create_record: %s', success)
        return success

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        params = {'per_page': 100}
        if rtype:
            params['type'] = rtype
        if name:
            params['name'] = self._full_name(name)
        # Sending the data filter to the Rackspace DNS API results in a 503 error
        # if content:
        #     params['data'] = content

        payload = self._get(
            '/domains/{0}/records'.format(self.domain_id), params)

        records = list(payload['records'])
        if content:
            records = [
                record for record in records if record['data'] == content]
        records = [{
            'type': record['type'],
            'name': record['name'],
            'ttl': record['ttl'],
            'content': record['data'],
            'id': record['id']
        } for record in records]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        data = {}
        if rtype:
            data['type'] = rtype
        if name:
            data['name'] = self._full_name(name)
        if content:
            data['data'] = content
        if self._get_lexicon_option('ttl'):
            data['ttl'] = self._get_lexicon_option('ttl')

        if identifier is None:
            records = self._list_records(rtype, name)
            if not records:
                raise Exception('Unable to find record to modify: ' + name)
            identifier = records[0]['id']

        self._put_and_wait(
            '/domains/{0}/records/{1}'.format(self.domain_id, identifier), data)

        # If it didn't raise from the http status code, then we're good
        LOGGER.debug('update_record: %s', identifier)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            self._delete_and_wait(
                '/domains/{0}/records/{1}'.format(self.domain_id, record_id)
            )

        # If it didn't raise from the http status code, then we're good
        success = True
        LOGGER.debug('delete_record: %s', success)
        return success

    # Helpers

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        LOGGER.debug('request tenant ID: %s', self._get_rackspace_option('auth_account'))
        full_url = (self.api_endpoint +
                    '/{0}' + url).format(self._get_rackspace_option('auth_account'))
        response = requests.request(action, full_url, params=query_params,
                                    data=json.dumps(data),
                                    headers={
                                        'X-Auth-Token': self._get_rackspace_option('auth_token'),
                                        'Content-Type': 'application/json'
                                    })
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    # Non-GET requests to the Rackspace CloudDNS API are asynchronous
    def _request_and_wait(self, action='POST', url='/', data=None, query_params=None):
        result = self._request(action, url, data, query_params)

        sleep_time = self._get_rackspace_option('sleep_time') or '1'
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
        response = requests.request('GET', payload['callbackUrl'], params={'showDetails': 'true'},
                                    data={},
                                    headers={
                                        'X-Auth-Token': self._get_rackspace_option('auth_token'),
                                        'Content-Type': 'application/json'})

        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    def _auth_request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}

        response = requests.request(action, self.auth_api_endpoint + url, params=query_params,
                                    data=json.dumps(data),
                                    headers={
                                        'Content-Type': 'application/json'
                                    })
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()
