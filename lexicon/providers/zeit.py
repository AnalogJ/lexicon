from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['zeit.world']


def ProviderParser(subparser):
    subparser.description = '''
        Zeit Provider requires a token to access its API.
        You can generate one for your account on the following URL:
        https://zeit.co/account/tokens'''
    subparser.add_argument('--auth-token', help='specify your API token')


class Provider(BaseProvider):
    """
    Implements the DNS Zeit provider.
    The API is quite simple: you can list all records, add one record or delete one record.
        - list is pretty straightforward: we get all records then filter for given parameters,
        - add uses directly the API to add a new record without any added complexity,
        - delete uses list + delete: we get the list of all records,
          filter on the given parameters and delete record by id,
        - update uses list + delete + add: we get the list of all records,
          find record for given identifier, then insert a new record and delete the old record.
    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.zeit.co/v2/domains'

    def authenticate(self):
        result = self._get('/{0}'.format(self.domain))

        if not result['uid']:
            raise Exception('Error, domain {0} not found'.format(self.domain))

        self.domain_id = result['uid']

    def list_records(self, type=None, name=None, content=None):
        result = self._get('/{0}/records'.format(self.domain))

        raw_records = result['records']
        if type:
            raw_records = [
                raw_record for raw_record in raw_records if raw_record['type'] == type]
        if name:
            raw_records = [
                raw_record for raw_record in raw_records if raw_record['name'] == self._relative_name(name)]
        if content:
            raw_records = [
                raw_record for raw_record in raw_records if raw_record['value'] == content]

        records = []
        for raw_record in raw_records:
            records.append({
                'id': raw_record['id'],
                'type': raw_record['type'],
                'name': self._full_name(raw_record['name']),
                'content': raw_record['value']
            })

        LOGGER.debug('list_records: %s', records)

        return records

    def create_record(self, type, name, content):
        # We ignore creation if a record already exists for given type/name/content
        records = self.list_records(type, name, content)
        if records:
            LOGGER.debug('create_record (ignored, duplicate): %s',
                         records[0]['id'])
            return True

        data = {
            'type': type,
            'name': self._relative_name(name),
            'value': content
        }

        result = self._post('/{0}/records'.format(self.domain), data)

        if not result['uid']:
            raise Exception('Error occured when inserting the new record.')

        LOGGER.debug('create_record: %s', result['uid'])

        return True

    def update_record(self, identifier, type=None, name=None, content=None):
        # Zeit do not allow to update a record, only add or remove.
        # So we get the corresponding record, dump or update its content and insert it as a new record.
        # Then we remove the old record.
        records = []
        if identifier:
            records = self.list_records()
            records = [
                record for record in records if record['id'] == identifier]
        else:
            records = self.list_records(type, name)

        if not records:
            raise Exception(
                'No record found for identifer: {0}'.format(identifier))

        if len(records) > 1:
            LOGGER.warn('Multiple records have been found for given parameters. Only first one will be updated (id: {0})'.format(
                records[0]['id']))

        data = {
            'type': type,
            'name': self._relative_name(name),
            'value': content
        }

        if not type:
            data['type'] = records[0]['type']
        if not name:
            data['name'] = self._relative_name(records[0]['name'])
        if not content:
            data['value'] = records[0]['content']

        result = self._post('/{0}/records'.format(self.domain), data)
        self._delete('/{0}/records/{1}'.format(self.domain, records[0]['id']))

        LOGGER.debug('update_record: %s => %s',
                     records[0]['id'], result['uid'])

        return True

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self.list_records(type, name, content)
            delete_record_ids = [record['id'] for record in records]
        else:
            delete_record_ids.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_ids)

        for delete_record_id in delete_record_ids:
            self._delete(
                '/{0}/records/{1}'.format(self.domain, delete_record_id))

        LOGGER.debug('delete_record: %s', True)

        return True

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        request = requests.request(action, self.api_endpoint + url,
                                   params=query_params,
                                   data=json.dumps(data),
                                   headers={'Authorization': 'Bearer {0}'.format(self._get_provider_option('auth_token'))})

        request.raise_for_status()
        return request.json()
