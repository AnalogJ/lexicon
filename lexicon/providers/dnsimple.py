"""Module provider for DNS Simple"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dnsimple.com']


def provider_parser(subparser):
    """Configure provider parser for DNS Simple"""
    subparser.add_argument(
        "--auth-token", help="specify api token for authentication")
    subparser.add_argument(
        "--auth-username", help="specify email address for authentication")
    subparser.add_argument(
        "--auth-password", help="specify password for authentication")
    subparser.add_argument(
        "--auth-2fa",
        help="specify two-factor auth token (OTP) to use with email/password authentication")


class Provider(BaseProvider):
    """Provider class for DNS Simple"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.account_id = None
        self.api_endpoint = self._get_provider_option(
            'api_endpoint') or 'https://api.dnsimple.com/v2'

    def _authenticate(self):

        payload = self._get('/accounts')

        if not payload[0]['id']:
            raise Exception('No account id found')

        for account in payload:
            dompayload = self._get(
                '/{0}/domains'.format(account['id']), query_params={'name_like': self.domain})
            if dompayload and dompayload[0]['id']:
                self.account_id = account['id']
                self.domain_id = dompayload[0]['id']

        if not self.account_id:
            raise Exception('No domain found like {}'.format(self.domain))

    # Create record. If record already exists with the same content, do nothing

    def _create_record(self, rtype, name, content):
        # check if record already exists
        existing_records = self._list_records(rtype, name, content)
        if len(existing_records) == 1:
            return True

        record = {
            'type': rtype,
            'name': self._relative_name(name),
            'content': content
        }
        if self._get_lexicon_option('ttl'):
            record['ttl'] = self._get_lexicon_option('ttl')
        if self._get_lexicon_option('priority'):
            record['priority'] = self._get_lexicon_option('priority')
        if self._get_provider_option('regions'):
            record['regions'] = self._get_provider_option('regions')

        payload = self._post(
            '/{0}/zones/{1}/records'.format(self.account_id, self.domain), record)

        LOGGER.debug('create_record: %s', 'id' in payload)
        return 'id' in payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        filter_query = {}
        if rtype:
            filter_query['type'] = rtype
        if name:
            filter_query['name'] = self._relative_name(name)
        payload = self._get(
            '/{0}/zones/{1}/records'.format(self.account_id, self.domain),
            query_params=filter_query)

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': '{}'.format(
                    self.domain) if record['name'] == "" else '{0}.{1}'.format(
                        record['name'],
                        self.domain),
                'ttl': record['ttl'],
                'content': record['content'],
                'id': record['id']}
            if record['priority']:
                processed_record['priority'] = record['priority']
            records.append(processed_record)

        if content:
            records = [
                record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        data = {}

        if identifier is None:
            records = self._list_records(rtype, name, content)
            identifiers = [record["id"] for record in records]
        else:
            identifiers = [identifier]

        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['content'] = content
        if self._get_lexicon_option('ttl'):
            data['ttl'] = self._get_lexicon_option('ttl')
        if self._get_lexicon_option('priority'):
            data['priority'] = self._get_lexicon_option('priority')
        if self._get_provider_option('regions'):
            data['regions'] = self._get_provider_option('regions')

        for one_identifier in identifiers:
            self._patch('/{0}/zones/{1}/records/{2}'
                        .format(self.account_id, self.domain, one_identifier), data)
            LOGGER.debug('update_record: %s', one_identifier)

        LOGGER.debug('update_record: %s', True)
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
            self._delete(
                '/{0}/zones/{1}/records/{2}'.format(self.account_id, self.domain, record_id))

        # is always True at this point; if a non 2xx response is returned, an error is raised.
        LOGGER.debug('delete_record: True')
        return True

    # Helpers

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        default_auth = None

        if self._get_provider_option('auth_token'):
            default_headers['Authorization'] = "Bearer {0}".format(
                self._get_provider_option('auth_token'))
        elif (self._get_provider_option('auth_username')
              and self._get_provider_option('auth_password')):
            default_auth = (self._get_provider_option(
                'auth_username'), self._get_provider_option('auth_password'))
            if self._get_provider_option('auth_2fa'):
                default_headers['X-Dnsimple-OTP'] = self._get_provider_option(
                    'auth_2fa')
        else:
            raise Exception('No valid authentication mechanism found')

        response = requests.request(action, self.api_endpoint + url, params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers,
                                    auth=default_auth)
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if response.text and response.json()['data'] is None:
            raise Exception('No data returned')

        return response.json()['data'] if response.text else None

    def _patch(self, url='/', data=None, query_params=None):
        return self._request('PATCH', url, data=data, query_params=query_params)
