from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['rage4.com']


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-username", help="specify email address for authentication")
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")


class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://rage4.com/rapi'

    def authenticate(self):

        payload = self._get('/getdomainbyname/', {'name': self.domain})

        if not payload['id']:
            raise Exception('No domain found')

        self.domain_id = payload['id']

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        # check if record already exists
        existing_records = self.list_records(type, name, content)
        if len(existing_records) == 1:
            return True

        record = {
            'id': self.domain_id,
            'name': self._full_name(name),
            'content': content,
            'type': type
        }
        if self._get_lexicon_option('ttl'):
            record['ttl'] = self._get_lexicon_option('ttl')

        payload = {}
        try:
            payload = self._post('/createrecord/', {}, record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                payload = {}

                # http 400 is ok here, because the record probably already exists
        LOGGER.debug('create_record: %s', payload['status'])
        return payload['status']

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {
            'id': self.domain_id
        }
        if name:
            filter['name'] = self._full_name(name)
        payload = self._get('/getrecords/', filter)

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': record['name'],
                'ttl': record['ttl'],
                'content': record['content'],
                'id': record['id']
            }
            records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if content:
            records = [
                record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'id': identifier
        }

        if name:
            data['name'] = self._full_name(name)
        if content:
            data['content'] = content
        if self._get_lexicon_option('ttl'):
            data['ttl'] = self._get_lexicon_option('ttl')
        # if type:
        #     raise 'Type updating is not supported by this provider.'

        payload = self._put('/updaterecord/', {}, data)

        LOGGER.debug('update_record: %s', payload['status'])
        return payload['status']

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
            payload = self._post('/deleterecord/', {'id': record_id})

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
        }
        default_auth = requests.auth.HTTPBasicAuth(self._get_provider_option(
            'auth_username'), self._get_provider_option('auth_token'))

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        return r.json()
