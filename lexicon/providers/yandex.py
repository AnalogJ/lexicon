from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

__author__ = 'Aliaksandr Kharkevich'
__license__ = 'MIT'
__contact__ = 'https://github.com/kharkevich'

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify PDD token (https://tech.yandex.com/domain/doc/concepts/access-docpage/)")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://pddimp.yandex.ru/api2/admin/dns')

    def authenticate(self):
        payload = self._get('/list?domain={0}'.format(self.options['domain']))
        if payload['success'] != "ok":
            raise Exception('No domain found')
        self.domain_id = self.options['domain']

    def create_record(self, type, name, content):
        if (type == 'CNAME') or (type == 'MX') or (type == 'NS'):
            content = content.rstrip('.') + '.' # make sure a the data is always a FQDN for CNAMe.

        querystring = 'domain={0}&type={1}&subdomain={2}&content={3}'.format(self.domain_id, type, self._relative_name(name), content)
        if self.options.get('ttl'):
            querystring += "&ttl={0}".format(self.options.get('ttl'))

        payload = self._post('/add', {},querystring)

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
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'].lower() == content.lower()]

        logger.debug('list_records: %s', records)
        return records

    # Just update existing record. Domain ID (domain) and Identifier (record_id) is mandatory
    def update_record(self, identifier, type=None, name=None, content=None):

        if not identifier:
            logger.debug('Domain ID (domain) and Identifier (record_id) is mandatory parameters for this case')
            return False
        
        data = ''
        if type:
            data += '&type={0}'.format(type)
        if name:
            data += '&subdomain={0}'.format(self._relative_name(name))
        if content:
            data += '&content={0}'.format(content)

        payload = self._post('/edit', {}, 'domain={0}&record_id={1}'.format(self.domain_id, identifier) + data)

        return self._check_exitcode(payload, 'update_record')

    # Delete an existing record.
    # If record does not exist (I'll hope), do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            logger.debug('records: %s', records)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')
        payload = self._post('/del', {}, 'domain={0}&record_id={1}'.format(self.domain_id, identifier))

        return self._check_exitcode(payload, 'delete_record')

    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'PddToken': self.options.get('auth_token')
        }

        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        r = requests.request(action, url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        if action == 'DELETE':
            return ''
        else:
            return r.json()


    def _check_exitcode(self, payload, title):
        if payload['success'] == 'ok':
            logger.debug('%s: %s', title, payload['success'])
            return True
        else:
            logger.debug('%s: %s', title, payload['error'])
            return False
