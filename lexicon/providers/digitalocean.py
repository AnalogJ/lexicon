"""Module provider for Digital Ocean"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['digitalocean.com']


def provider_parser(subparser):
    """Configure provider parser for Digital Ocean"""
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")


class Provider(BaseProvider):
    """Provider class for Digital Ocean"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.digitalocean.com/v2'

    def _authenticate(self):
        self._get('/domains/{0}'.format(self.domain))
        self.domain_id = self.domain

    def _create_record(self, rtype, name, content):
        # check if record already exists
        if not self._list_records(rtype, name, content):
            record = {
                'type': rtype,
                'name': self._relative_name(name),
                'data': content,

            }
            if rtype == 'CNAME':
                # make sure a the data is always a FQDN for CNAMe.
                record['data'] = record['data'].rstrip('.') + '.'

            self._post(
                '/domains/{0}/records'.format(self.domain_id), record)
        LOGGER.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        url = '/domains/{0}/records'.format(self.domain_id)
        records = []
        payload = {}

        next_url = url
        while next_url is not None:
            payload = self._get(next_url)
            if 'links' in payload \
                    and 'pages' in payload['links'] \
                    and 'next' in payload['links']['pages']:
                next_url = payload['links']['pages']['next']
            else:
                next_url = None

            for record in payload['domain_records']:
                processed_record = {
                    'type': record['type'],
                    'name': "{0}.{1}".format(record['name'], self.domain_id),
                    'ttl': '',
                    'content': record['data'],
                    'id': record['id']
                }
                records.append(processed_record)

        if rtype:
            records = [record for record in records if record['type'] == rtype]
        if name:
            records = [record for record in records if record['name']
                       == self._full_name(name)]
        if content:
            records = [
                record for record in records if record['content'].lower() == content.lower()]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        data = {}
        if rtype:
            data['type'] = rtype
        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['data'] = content

        self._put(
            '/domains/{0}/records/{1}'.format(self.domain_id, identifier), data)

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
                '/domains/{0}/records/{1}'.format(self.domain_id, record_id))

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
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(self._get_provider_option('auth_token'))
        }
        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        response = requests.request(action, url, params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers)
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if action == 'DELETE':
            return ''
        return response.json()
