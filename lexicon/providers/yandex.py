"""Module provider for Yandex"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


__author__ = 'Aliaksandr Kharkevich'
__license__ = 'MIT'
__contact__ = 'https://github.com/kharkevich'

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['yandex.com']


def provider_parser(subparser):
    """Generate parser provider for Yandex"""
    subparser.add_argument(
        "--auth-token",
        help="specify PDD token (https://tech.yandex.com/domain/doc/concepts/access-docpage/)")


class Provider(BaseProvider):
    """Provider class for Yandex"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://pddimp.yandex.ru/api2/admin/dns'

    def _authenticate(self):
        payload = self._get('/list?domain={0}'.format(self.domain))
        if payload['success'] != "ok":
            raise Exception('No domain found')
        self.domain_id = self.domain

    def _create_record(self, rtype, name, content):
        if rtype in ('CNAME', 'MX', 'NS'):
            # make sure a the data is always a FQDN for CNAMe.
            content = content.rstrip('.') + '.'

        querystring = 'domain={0}&type={1}&subdomain={2}&content={3}'.format(
            self.domain_id, rtype, self._relative_name(name), content)
        if self._get_lexicon_option('ttl'):
            querystring += "&ttl={0}".format(self._get_lexicon_option('ttl'))

        payload = self._post('/add', {}, querystring)

        return self._check_exitcode(payload, 'create_record')

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        url = '/list?domain={0}'.format(self.domain_id)
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

            for record in payload['records']:
                processed_record = {
                    'type': record['type'],
                    'name': "{0}.{1}".format(record['subdomain'], self.domain_id),
                    'ttl': record['ttl'],
                    'content': record['content'],
                    'id': record['record_id']
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

    # Just update existing record. Domain ID (domain) and Identifier (record_id) is mandatory
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        if not identifier:
            LOGGER.debug(
                'Domain ID (domain) and Identifier (record_id) '
                'is mandatory parameters for this case')
            return False

        data = ''
        if rtype:
            data += '&type={0}'.format(rtype)
        if name:
            data += '&subdomain={0}'.format(self._relative_name(name))
        if content:
            data += '&content={0}'.format(content)

        payload = self._post(
            '/edit', {}, 'domain={0}&record_id={1}'.format(self.domain_id, identifier) + data)

        return self._check_exitcode(payload, 'update_record')

    # Delete an existing record.
    # If record does not exist (I'll hope), do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            self._post(
                '/del', {}, 'domain={0}&record_id={1}'.format(self.domain_id, record_id))

        # return self._check_exitcode(payload, 'delete_record')
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
            'PddToken': self._get_provider_option('auth_token')
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

    def _check_exitcode(self, payload, title):  # pylint: disable=no-self-use
        if payload['success'] == 'ok':
            LOGGER.debug('%s: %s', title, payload['success'])
            return True
        if payload['error'] == 'record_exists':
            LOGGER.debug('%s: %s', title, True)
            return True
        LOGGER.debug('%s: %s', title, payload['error'])
        return False
