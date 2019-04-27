"""Module provider for Namesilo"""
from __future__ import absolute_import
import logging
from xml.etree import ElementTree

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['namesilo.com']


def provider_parser(subparser):
    """Configure provider parser for Namesilo"""
    subparser.add_argument(
        "--auth-token", help="specify key for authentication")


class Provider(BaseProvider):
    """Provider class for Namesilo"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = self._get_provider_option(
            'api_endpoint') or 'https://www.namesilo.com/api'

    def _authenticate(self):
        self._get('/getDomainInfo', {'domain': self.domain})
        self.domain_id = self.domain

    # Create record. If record already exists with the same content, do nothing'

    def _create_record(self, rtype, name, content):
        record = {
            'domain': self.domain_id,
            'rrhost': self._relative_name(name),
            'rrtype': rtype,
            'rrvalue': content
        }
        if self._get_lexicon_option('ttl'):
            record['rrttl'] = self._get_lexicon_option('ttl')
        try:
            self._get('/dnsAddRecord', record)
        except ValueError as err:
            # noop if attempting to create record that already exists.
            LOGGER.debug('Ignoring error: %s', err)

        LOGGER.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        query = {'domain': self.domain_id}

        payload = self._get('/dnsListRecords', query)
        records = []
        for record in payload.find('reply').findall('resource_record'):
            processed_record = {
                'type': record.find('type').text,
                'name': record.find('host').text,
                'ttl': record.find('ttl').text,
                'content': record.find('value').text,
                'id': record.find('record_id').text
            }
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
            'rrid': identifier
        }
        # if rtype:
        #     data['type'] = rtype
        if name:
            data['rrhost'] = self._relative_name(name)
        if content:
            data['rrvalue'] = content
        if self._get_lexicon_option('ttl'):
            data['rrttl'] = self._get_lexicon_option('ttl')

        self._get('/dnsUpdateRecord', data)

        LOGGER.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        data = {
            'domain': self.domain_id
        }

        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            data['rrid'] = record_id
            self._get('/dnsDeleteRecord', data)

        LOGGER.debug('delete_record: %s', True)
        return True

    # Helpers

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        query_params['version'] = 1
        query_params['type'] = 'xml'
        query_params['key'] = self._get_provider_option('auth_token')
        response = requests.request(action, self.api_endpoint +
                                    url, params=query_params)
        # data=json.dumps(data))
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        tree = ElementTree.ElementTree(ElementTree.fromstring(response.content))
        root = tree.getroot()
        if root.find('reply').find('code').text == '280':
            raise ValueError('An error occurred: {0}, {1}'.format(
                root.find('reply').find('detail').text, root.find('reply').find('code').text))
        if root.find('reply').find('code').text != '300':
            raise Exception('An error occurred: {0}, {1}'.format(
                root.find('reply').find('detail').text, root.find('reply').find('code').text))

        return root
