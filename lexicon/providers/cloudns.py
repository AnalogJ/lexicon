from __future__ import absolute_import
from __future__ import print_function

import logging
import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    identity_group = subparser.add_mutually_exclusive_group()
    identity_group.add_argument("--auth-id", help="specify user id used to authenticate")
    identity_group.add_argument("--auth-subid", help="specify subuser id used to authenticate")
    identity_group.add_argument("--auth-subuser", help="specify subuser name used to authenticate")
    subparser.add_argument("--auth-password", help="specify password used to authenticate")
    subparser.add_argument("--weight", help="specify the SRV record weight")
    subparser.add_argument("--port", help="specify the SRV record port")


class Provider(BaseProvider):
    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.cloudns.net')

    def authenticate(self):
        payload = self._get('/dns/get-zone-info.json', {'domain-name': self.options['domain']})
        self.domain_id = payload['name']
        logger.debug('authenticate: %s', payload)

    def create_record(self, type, name, content):
        # Skip execution if such a record already exists
        existing_records = self.list_records(type, name, content)
        if len(existing_records) > 0:
            return True

        # Build parameters for adding a new record
        params = {
            'domain-name': self.domain_id,
            'record-type': type,
            'host': self._relative_name(name),
            'record': content
        }
        if self.options['ttl']:
            params['ttl'] = self.options['ttl']
        if self.options['priority']:
            params['priority'] = self.options['priority']
        if self.options['weight']:
            params['weight'] = self.options['weight']
        if self.options['port']:
            params['port'] = self.options['port']

        # Add new record by calling the ClouDNS API
        payload = self._post('/dns/add-record.json', params)
        logger.debug('create_record: %s', payload)

        # Error handling is already covered by self._request
        return True

    def list_records(self, type=None, name=None, content=None):
        # Build parameters to make use of the built-in API filtering
        params = {'domain-name': self.domain_id}
        if type:
            params['type'] = type
        if name:
            params['host'] = self._relative_name(name)

        # Fetch and parse all records for the given zone
        payload = self._get('/dns/records.json', params)
        payload = payload if not isinstance(payload, list) else {}
        records = []
        for record in payload.values():
            records.append({
                'type': record['type'],
                'name': self._full_name(record['host']),
                'ttl': record['ttl'],
                'content': record['record'],
                'id': record['id']
            })

        # Filter by content manually as API does not support that
        if content:
            records = [record for record in records if record['content'] == content]

        # Print records as debug output and return them
        logger.debug('list_records: %s', records)
        return records

    def update_record(self, identifier, type=None, name=None, content=None):
        # Try to find record if no identifier was specified
        if not identifier:
            identifier = self._find_record_identifier(type, name, None)

        # Build parameters for updating an existing record
        params = {'domain-name': self.domain_id, 'record-id': identifier}
        if name:
            params['host'] = self._relative_name(name)
        if content:
            params['record'] = content
        if self.options.get('ttl'):
            params['ttl'] = self.options.get('ttl')
        if self.options['priority']:
            params['priority'] = self.options['priority']
        if self.options['weight']:
            params['weight'] = self.options['weight']
        if self.options['port']:
            params['port'] = self.options['port']

        # Update existing record by calling the ClouDNS API
        payload = self._post('/dns/mod-record.json', params)
        logger.debug('update_record: %s', payload)

        # Error handling is already covered by self._request
        return True

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        # Try to find record if no identifier was specified
        delete_record_id = []
        if not identifier:
            records = self.list_records(type, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        logger.debug('delete_records: %s', delete_record_id)

        for record_id in delete_record_id:
            # Delete existing record by calling the ClouDNS API
            payload = self._post('/dns/delete-record.json', {'domain-name': self.domain_id, 'record-id': record_id})

        logger.debug('delete_record: %s', True)

        # Error handling is already covered by self._request
        return True

    def _is_given_option(self, key):
        fallback_fn = self.engine_overrides.get('fallbackFn', (lambda x: None))
        return self.options[key] and self.options[key] != fallback_fn(key)

    def _build_authentication_data(self):
        if not self.options['auth_password']:
            raise Exception('No valid authentication data passed, expected: auth-password')

        if self._is_given_option('auth_id'):
            return {'auth-id': self.options['auth_id'], 'auth-password': self.options['auth_password']}
        elif self._is_given_option('auth_subid'):
            return {'sub-auth-id': self.options['auth_subid'], 'auth-password': self.options['auth_password']}
        elif self._is_given_option('auth_subuser'):
            return {'sub-auth-user': self.options['auth_subuser'], 'auth-password': self.options['auth_password']}
        elif self.options['auth_id'] or self.options['auth_subid'] or self.options['auth_subuser']:
            # All the options were passed with a fallback value, return an empty dictionary.
            return {}
        else:
            raise Exception('No valid authentication data passed, expected: auth-id, auth-subid, auth-subuser')

    def _find_record_identifier(self, type, name, content):
        records = self.list_records(type, name, content)
        logger.debug('records: %s', records)
        if len(records) == 1:
            return records[0]['id']
        else:
            raise Exception('Record identifier could not be found.')

    def _request(self, action='GET', url='/', data=None, query_params=None):
        # Set default values for missing arguments
        data = data if data else {}
        query_params = query_params if query_params else {}

        # Merge authentication data into request
        if action == 'GET':
            query_params.update(self._build_authentication_data())
        else:
            data.update(self._build_authentication_data())

        # Fire request against ClouDNS API and parse result as JSON
        r = requests.request(action, self.api_endpoint + url, params=query_params, data=data)
        r.raise_for_status()
        payload = r.json()

        # Check ClouDNS specific status code and description
        if 'status' in payload and 'statusDescription' in payload and payload['status'] != 'Success':
            raise Exception('ClouDNS API request has failed: ' + payload['statusDescription'])

        # Return payload
        return payload
