from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dnspark.com']


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-username", help="specify api key for authentication")
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")


class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.dnspark.com/v2'

    def authenticate(self):

        payload = self._get('/dns/{0}'.format(self.domain))

        if not payload['additional']['domain_id']:
            raise Exception('No domain found')

        self.domain_id = payload['additional']['domain_id']

    # Create record. If record already exists with the same content, do nothing'

    def create_record(self, type, name, content):
        record = {
            'rname': self._relative_name(name),
            'rtype': type,
            'rdata': content
        }
        payload = {}
        try:
            payload = self._post('/dns/{0}'.format(self.domain_id), record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                payload = {}
            raise e
            # http 400 is ok here, because the record probably already exists
        LOGGER.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._get('/dns/{0}'.format(self.domain_id))
        records = []
        for record in payload['records']:
            processed_record = {
                'type': record['rtype'],
                'name': record['rname'],
                'ttl': record['ttl'],
                'content': record['rdata'],
                'id': record['record_id']
            }
            records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name']
                       == self._full_name(name)]
        if content:
            records = [
                record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'ttl': self._get_lexicon_option('ttl')
        }
        if type:
            data['rtype'] = type
        if name:
            data['rname'] = self._relative_name(name)
        if content:
            data['rdata'] = content

        payload = self._put('/dns/{0}'.format(identifier), data)

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
            payload = self._delete('/dns/{0}'.format(record_id))

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
            'Content-Type': 'application/json'
        }
        default_auth = (self._get_provider_option('auth_username'),
                        self._get_provider_option('auth_token'))

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        return r.json()
