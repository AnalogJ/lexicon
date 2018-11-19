from __future__ import absolute_import
import contextlib
import hmac
import json
import locale
import logging
from builtins import bytes
from email.utils import formatdate
from hashlib import sha1

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dnsmadeeasy']


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-username", help="specify username for authentication")
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")


class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = self._get_provider_option(
            'api_endpoint') or 'https://api.dnsmadeeasy.com/V2.0'

    def authenticate(self):

        try:
            payload = self._get('/dns/managed/name',
                                {'domainname': self.domain})
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                payload = {}
            else:
                raise e

        if not payload or not payload['id']:
            raise Exception('No domain found')

        self.domain_id = payload['id']

    # Create record. If record already exists with the same content, do nothing'

    def create_record(self, type, name, content):
        record = {
            'type': type,
            'name': self._relative_name(name),
            'value': content,
            'ttl': self._get_lexicon_option('ttl')
        }
        payload = {}
        try:
            payload = self._post(
                '/dns/managed/{0}/records/'.format(self.domain_id), record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 400:
                raise

                # http 400 is ok here, because the record probably already exists
        LOGGER.debug('create_record: %s', 'name' in payload)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}
        if type:
            filter['type'] = type
        if name:
            filter['recordName'] = self._relative_name(name)
        payload = self._get(
            '/dns/managed/{0}/records'.format(self.domain_id), filter)

        records = []
        for record in payload['data']:
            processed_record = {
                'type': record['type'],
                'name': '{0}.{1}'.format(record['name'], self.domain),
                'ttl': record['ttl'],
                'content': record['value'],
                'id': record['id']
            }

            processed_record = self._clean_TXT_record(processed_record)
            records.append(processed_record)

        if content:
            records = [
                record for record in records if record['content'].lower() == content.lower()]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'id': identifier,
            'ttl': self._get_lexicon_option('ttl')
        }

        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['value'] = content
        if type:
            data['type'] = type

        payload = self._put(
            '/dns/managed/{0}/records/{1}'.format(self.domain_id, identifier), data)

        LOGGER.debug('update_record: %s', True)
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

        LOGGER.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            payload = self._delete(
                '/dns/managed/{0}/records/{1}'.format(self.domain_id, record_id))

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug('delete_record: %s', True)
        return True

    # Helpers

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'x-dnsme-apiKey': self._get_provider_option('auth_username')
        }
        default_auth = None

        # Date string in HTTP format e.g. Sat, 12 Feb 2011 20:59:04 GMT
        request_date = formatdate(usegmt=True)

        hashed = hmac.new(bytes(self._get_provider_option('auth_token'), 'ascii'),
                          bytes(request_date, 'ascii'), sha1)

        default_headers['x-dnsme-requestDate'] = request_date
        default_headers['x-dnsme-hmac'] = hashed.hexdigest()

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()

        # PUT and DELETE actions dont return valid json.
        if action == 'DELETE' or action == 'PUT':
            return r.text
        return r.json()
