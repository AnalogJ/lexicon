"""Module provider for Dynu.com"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dynu.com']


def provider_parser(subparser):
    """Module provider for Dynu.com"""
    subparser.add_argument(
        "--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):
    """Provider class for Dynu.com"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.dynu.com/v2'

    def _authenticate(self):
        data = self._get('/dns')
        domains = data['domains']
        for domain in domains:
            if domain['name'].lower() == self.domain.lower():
                self.domain_id = domain['id']
                break
        if not self.domain_id:
            raise Exception('No matching domain found')

    # Create record. If record already exists with the same content, do nothing.
    def _create_record(self, rtype, name, content):
        record = {
            'recordType': rtype,
            'textData': content,
            'state': True,
        }
        if name:
            record['nodeName'] = self._relative_name(name)

        if self._get_lexicon_option('ttl'):
            record['ttl'] = self._get_lexicon_option('ttl')

        try:
            payload = self._post('/dns/{0}/record'.format(self.domain_id), record)
        except requests.exceptions.HTTPError as error:
            # HTTP 501 is expected when a record with the same type and content is sent to the
            # server.
            if error.response.status_code == 501:
                pass
            else:
                raise error
        created = self._format_record(payload)
        LOGGER.debug('create_record: %s', created)
        return created

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get('/dns/{0}/record'.format(self.domain_id))

        records = []
        for record in payload['dnsRecords']:
            processed_record = self._format_record(record)
            records.append(processed_record)

        len_all = len(records)

        if rtype:
            records = [record for record in records if record['type'] == rtype]

        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]

        if content:
            records = [record for record in records if record['content'] == content]

        len_removed = len_all - len(records)
        if len_removed:
            LOGGER.debug('list_records: removed %d, total %d', len_removed, len_all)

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        record = {
            'recordType': rtype,
            'name': name,
            'content': content,
        }

        payload = self._post('/dns/{0}/record/{1}'.format(self.domain_id, identifier), record)
        update = self._format_record(payload)
        LOGGER.debug('update_record: %s', update)
        return update

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
            self._delete('/dns/{0}/record/{1}'.format(self.domain_id, record_id))

        LOGGER.debug('delete_record: %s', True)
        return True

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data:
            data = json.dumps(data)
        # Dynu API does not respond to query parameters at all, so we ignore them
        response = requests.request(action, self.api_endpoint + url, data=data,
                                    headers={
                                        'API-Key': self._get_provider_option('auth_token'),
                                        'Accept': 'application/json',
                                        'Content-Type': 'application/json'
                                    })
        response.raise_for_status()
        return response.json()

    # Takes a Dynu.com record and puts it into lexicon-shape
    @staticmethod
    def _format_record(record):
        return {
            'id': record['id'],
            'type': record['recordType'],
            'name': record['hostname'],
            'content': record['content'],
            'ttl': record['ttl'],
        }
