from __future__ import absolute_import, print_function
import hashlib
import json
import logging
import random
import string
import time
from urllib.parse import urlencode

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['nearlyfreespeech.net']


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-username", help="specify username used to authenticate")
    subparser.add_argument(
        "--auth-token", help="specify token used to authenticate")


SALT_SHAKER = string.ascii_letters + string.digits


class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.nearlyfreespeech.net'
        self.shortname = None

    def authenticate(self):
        self._post('/dns/{0}/listRRs'.format(self.domain))
        self.domain_id = self.domain

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        existing_record = self.list_records(type, name, content)
        if len(existing_record) > 0:
            # Do nothing if the record already exists.
            # The creation call can fail for a variety of reasons, so
            # the safest thing to do is check if the record already exists
            return True

        self._do_create(type, name, content)
        LOGGER.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        params = {}
        if type is not None:
            params['type'] = type
        if name is not None:
            params['name'] = self._relative_name(name)
        if content is not None:
            params['data'] = content

        url = '/dns/{0}/listRRs'.format(self.domain_id)
        records = self._post(url, params)
        records = [{
            'type': r['type'],
            'name': self._full_name(r['name']),
            'ttl': r['ttl'],
            'content': r['data'],
            'id': hashlib.sha1(''.join([r['type'], r['name'], r['data']]).encode('utf-8')).hexdigest()
        } for r in records]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.

    def update_record(self, identifier, type=None, name=None, content=None):
        if identifier is not None:
            records = self.list_records()
            to_delete = next(
                (r for r in records if r['id'] == identifier), None)
            if to_delete is None:
                raise ValueError('No record with that identifier.')
        else:
            # Check name and type
            matching_records = self.list_records(type=type, name=name)
            if len(matching_records) > 1:
                raise ValueError(
                    'More than one record exists with that type and name. Try specifying an identifier.')
            to_delete = matching_records[0]

        self._do_delete(to_delete['type'],
                        to_delete['name'], to_delete['content'])
        self._do_create(type, name, content)
        LOGGER.debug('update_record: %s', True)
        return True

    # Delete an existing record
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        matching_records = self.list_records(type, name, content)
        if identifier is not None:
            to_delete = next(
                (r for r in matching_records if r['id'] == identifier), None)
            if to_delete is None:
                raise ValueError('No record with that identifier.')
            to_delete = [to_delete]
        else:
            to_delete = matching_records

        for d in to_delete:
            self._do_delete(d['type'], d['name'], d['content'])

        LOGGER.debug('delete_record: %s', True)
        return True

    def _do_create(self, type, name, content):
        record = {
            'name': self._relative_name(name),
            'type': type,
            'data': content
        }

        ttl = self._get_lexicon_option('ttl')
        if ttl:
            record['ttl'] = ttl

        self._post('/dns/{0}/addRR'.format(self.domain_id), record)
        return True

    def _do_delete(self, type=None, name=None, content=None):
        url = '/dns/{0}/removeRR'.format(self.domain_id)
        record = {
            'name': self._relative_name(name),
            'type': type,
            'data': content
        }
        self._post(url, record)
        return True

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is not None:
            body = urlencode(data)
            hashed_body = hashlib.sha1(body.encode('utf-8')).hexdigest()
        else:
            hashed_body = hashlib.sha1().hexdigest()

        timestamp = str(int(time.time()))
        salt = ''.join(random.choice(SALT_SHAKER) for _ in range(16))
        hash_items = [self._get_provider_option(
            'auth_username'), timestamp, salt, self._get_provider_option('auth_token'), url, hashed_body]
        auth_hash = hashlib.sha1(
            ';'.join(hash_items).encode('utf-8')).hexdigest()
        auth_value = ';'.join([self._get_provider_option(
            'auth_username'), timestamp, salt, auth_hash])
        auth_header = {
            'X-NFSN-Authentication': auth_value
        }

        r = requests.request(action, ''.join([self.api_endpoint, url]),
                             data=data,
                             headers=auth_header)
        r.raise_for_status()
        if r.content:
            return r.json()
        else:
            return {}
