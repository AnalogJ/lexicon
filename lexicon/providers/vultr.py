"""Module provider for Vultr"""
from __future__ import absolute_import
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['vultr.com']


def provider_parser(subparser):
    """Configure provider parser for Vultr"""
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")


class Provider(BaseProvider):
    """Provider class for Vultr"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.vultr.com/v1'

    def _authenticate(self):
        payload = self._get('/dns/list')

        if not [item for item in payload if item['domain'] == self.domain]:
            raise Exception('No domain found')

        self.domain_id = self.domain

    # Create record. If record already exists with the same content, do nothing'

    def _create_record(self, rtype, name, content):
        record = {
            'type': rtype,
            'domain': self.domain_id,
            'name': self._relative_name(name),
            'priority': 0
        }
        if rtype == 'TXT':
            record['data'] = "\"{0}\"".format(content)
        else:
            record['data'] = content
        if self._get_lexicon_option('ttl'):
            record['ttl'] = self._get_lexicon_option('ttl')
        self._post('/dns/create_record', record)

        LOGGER.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get('/dns/records', {'domain': self.domain_id})
        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': "{0}.{1}".format(record['name'], self.domain_id),
                'ttl': record.get('ttl', self._get_lexicon_option('ttl')),
                'content': record['data'],
                'id': record['RECORDID']
            }
            processed_record = self._clean_TXT_record(processed_record)
            records.append(processed_record)

        if rtype:
            records = [record for record in records if record['type'] == rtype]
        if name:
            records = [record for record in records if record['name']
                       == self._full_name(name)]
        if content:
            records = [
                record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        data = {
            'domain': self.domain_id,
            'RECORDID': identifier,
            'ttl': self._get_lexicon_option('ttl')
        }
        # if rtype:
        #     data['type'] = rtype
        if name:
            data['name'] = self._relative_name(name)
        if content:
            if rtype == 'TXT':
                data['data'] = "\"{0}\"".format(content)
            else:
                data['data'] = content

        self._post('/dns/update_record', data)

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
            data = {
                'domain': self.domain_id,
                'RECORDID': record_id
            }
            self._post('/dns/delete_record', data)

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug('delete_record: %s', True)
        return True

    # Helpers

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        default_headers = {
            'Accept': 'application/json',
            # 'Content-Type': 'application/json',
            'API-Key': self._get_provider_option('auth_token')
        }

        response = requests.request(action, self.api_endpoint + url, params=query_params,
                                    data=data,
                                    headers=default_headers)
        # if the request fails for any reason, throw an error.
        response.raise_for_status()

        if action in ('DELETE', 'PUT', 'POST'):
            # vultr handles succss/failure via HTTP Codes, Only GET returns a response.
            return response.text
        return response.json()
