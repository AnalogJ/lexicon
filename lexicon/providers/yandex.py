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


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-token", help="specify PDD token (https://tech.yandex.com/domain/doc/concepts/access-docpage/)")


class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://pddimp.yandex.ru/api2/admin/dns'

    def authenticate(self):
        payload = self._get('/list?domain={0}'.format(self.domain))
        if payload['success'] != "ok":
            raise Exception('No domain found')
        self.domain_id = self.domain

    def create_record(self, type, name, content):
        if (type == 'CNAME') or (type == 'MX') or (type == 'NS'):
            # make sure a the data is always a FQDN for CNAMe.
            content = content.rstrip('.') + '.'

        querystring = 'domain={0}&type={1}&subdomain={2}&content={3}'.format(
            self.domain_id, type, self._relative_name(name), content)
        if self._get_lexicon_option('ttl'):
            querystring += "&ttl={0}".format(self._get_lexicon_option('ttl'))

        payload = self._post('/add', {}, querystring)

        return self._check_exitcode(payload, 'create_record')

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        url = '/list?domain={0}'.format(self.domain_id)
        records = []
        payload = {}

        next = url
        while next is not None:
            payload = self._get(next)
            if 'links' in payload \
                    and 'pages' in payload['links'] \
                    and 'next' in payload['links']['pages']:
                next = payload['links']['pages']['next']
            else:
                next = None

            for record in payload['records']:
                processed_record = {
                    'type': record['type'],
                    'name': "{0}.{1}".format(record['subdomain'], self.domain_id),
                    'ttl': record['ttl'],
                    'content': record['content'],
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
                record for record in records if record['content'].lower() == content.lower()]

        LOGGER.debug('list_records: %s', records)
        return records

    # Just update existing record. Domain ID (domain) and Identifier (record_id) is mandatory
    def update_record(self, identifier, type=None, name=None, content=None):

        if not identifier:
            LOGGER.debug(
                'Domain ID (domain) and Identifier (record_id) is mandatory parameters for this case')
            return False

        data = ''
        if type:
            data += '&type={0}'.format(type)
        if name:
            data += '&subdomain={0}'.format(self._relative_name(name))
        if content:
            data += '&content={0}'.format(content)

        payload = self._post(
            '/edit', {}, 'domain={0}&record_id={1}'.format(self.domain_id, identifier) + data)

        return self._check_exitcode(payload, 'update_record')

    # Delete an existing record.
    # If record does not exist (I'll hope), do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self.list_records(type, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            payload = self._post(
                '/del', {}, 'domain={0}&record_id={1}'.format(self.domain_id, record_id))

        # return self._check_exitcode(payload, 'delete_record')
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
            'PddToken': self._get_provider_option('auth_token')
        }

        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        r = requests.request(action, url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        if action == 'DELETE':
            return ''
        else:
            return r.json()

    def _check_exitcode(self, payload, title):
        if payload['success'] == 'ok':
            LOGGER.debug('%s: %s', title, payload['success'])
            return True
        elif payload['error'] == 'record_exists':
            LOGGER.debug('%s: %s', title, True)
            return True
        else:
            LOGGER.debug('%s: %s', title, payload['error'])
            return False
