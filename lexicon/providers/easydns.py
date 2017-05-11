from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify username used to authenticate")
    subparser.add_argument("--auth-token", help="specify token used authenticate")


class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://rest.easydns.net')

    def authenticate(self):

        payload = self._get('/domain/{0}'.format(self.options['domain']))

        if payload['data']['exists'] == 'N':
            raise Exception('No domain found')

        self.domain_id = payload['data']['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'type': type,
            'domain': self.domain_id,
            'host': self._relative_name(name),
            'ttl': self.options['ttl'],
            'prio': 0,
            'rdata': content
        }
        payload = {}
        try:
            payload = self._put('/zones/records/add/{0}/{1}'.format(self.domain_id, type), record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                payload = {}

                # http 400 is ok here, because the record probably already exists
        logger.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._get('/zones/records/all/{0}'.format(self.domain_id))
        records = []
        for record in payload['data']:
            processed_record = {
                'type': record['type'],
                'name': "{0}.{1}".format(record['host'], record['domain']),
                'ttl': record['ttl'],
                'content': record['rdata'],
                'id': record['id']
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
            'ttl': self.options['ttl']
        }
        if type:
            data['type'] = type
        if name:
            data['host'] = self._relative_name(name)
        if content:
            data['rdata'] = content

        payload = self._post('/zones/records/{0}'.format(identifier), data)

        logger.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            logger.debug('records: %s', records)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')
        payload = self._delete('/zones/records/{0}/{1}'.format(self.domain_id, identifier))

        # is always True at this point, if a non 200 response is returned an error is raised.
        logger.debug('delete_record: %s', True)
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        query_params['format'] = 'json'
        query_params['_user'] = self.options['auth_username']
        query_params['_key'] = self.options['auth_token']
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
