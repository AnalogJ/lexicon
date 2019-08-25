"""Module provider for DirectAdmin hosts"""
import logging
import warnings

import requests
from requests.auth import HTTPBasicAuth

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

# DirectAdmin is not tied to a specific domain, so there is nothing to specify here
NAMESERVER_DOMAINS = []

def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument(
        "--auth-password",
        help="specify password for authentication (or login key for two-factor authentication)"
    )

    subparser.add_argument(
        "--auth-username",
        help="specify username for authentication"
    )

    subparser.add_argument(
        "--endpoint",
        help="specify the DirectAdmin endpoint"
    )

# See https://www.directadmin.com/features.php?id=504 for the specification of
# the URIs for the different operations
class Provider(BaseProvider):
    """Provider class for DirectAdmin"""
    def __init__(self, config):
        super(Provider, self).__init__(config)

        self.endpoint = self._get_provider_option('endpoint')
        if self.endpoint is None:
            raise Exception('Specify endpoint of DirectAdmin')

    def _authenticate(self):
        try:
            response = self._get('/CMD_API_SHOW_DOMAINS')
        except requests.exceptions.HTTPError as err:
            # A 401 error will be returned in case of incorrect or missing
            # credentials
            cause = err.response.json()['error']
            raise Exception(cause)

        # The response is a URL encoded array containing all available domains
        domains = [domain.split('=').pop() for domain in response.split('&')]

        try:
            self.domain_id = domains.index(self.domain)
        except:
            raise Exception('Domain {0} not found'.format(self.domain))

    def _create_record(self, rtype, name, content):
        # Refuse to create duplicate records
        existing_records = self._list_records(rtype, name, content)
        if existing_records:
            return True

        query_params = {
            'action': 'add', 'json': 'yes',
            'name': '{0}.'.format(self._full_name(name)), 'type': rtype,
            'value': content
        }

        if self._get_lexicon_option('ttl'):
            query_params['ttl'] = self._get_lexicon_option('ttl')

        try:
            response = self._get('/CMD_API_DNS_CONTROL', query_params)
        except requests.exceptions.HTTPError:
            response = {'success': 'Create Failed'}

        LOGGER.debug('create_record: %s', response)

        return response['success'].lower().find('added') >= 0

    def _list_records(self, rtype=None, name=None, content=None):
        response = {'records': []}
        try:
            response = self._get('/CMD_API_DNS_CONTROL', {'json': 'yes'})
        except requests.exceptions.HTTPError as err:
            warnings.warn(err.response.text)
            raise

        records = [self._parse_response_record(record) for record in response['records']]
        if rtype:
            records = [record for record in records if record['type'] == rtype]
        if name:
            cmp_name = self._full_name(name.lower())
            records = [record for record in records if record['name'] == cmp_name]
        if content:
            records = [record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)

        return records

    def _parse_response_record(self, response_record):
        # Most fields in a record response match, except for content which is
        # value
        return {
            'content': response_record['value'],
            'id': response_record['combined'],
            'name': self._full_name(response_record['name']),
            # 4 hours appears to be the default shown by DirectAdmin if no TTL
            # is set
            'ttl': response_record.get('ttl', 14400),
            'type': response_record['type']
        }

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # Editing a record is a combination of removing the old record and
        # adding a new one, but specifying 'edit' as the action while passing
        # all parameters necessary for both deletion and creation

        if not identifier:
            # The identifier of the original record to edit is necessary to be
            # able to create the appropriate delete payload
            original_records = self.list_records(rtype, name)
            if len(original_records) > 1:
                warnings.warn('Found multiple records to edited. Cannot continue...')
                return False

            if not original_records:
                warnings.warn('Found no records to edit. Cannot continue...')
                return False

            identifier = original_records[0]['id']

        delete_key = self._determine_delete_key(identifier, rtype)

        query_params = {
            'action': 'edit', 'json': 'yes',
            delete_key: identifier,
            'name': '{0}.'.format(self._full_name(name)), 'type': rtype,
            'value': content
        }

        try:
            response = self._get('/CMD_API_DNS_CONTROL', query_params)
        except requests.exceptions.HTTPError:
            response = {'success': 'Update Failed'}

        LOGGER.debug('update_record: %s', response)

        return response['success'].lower().find('added') > 0

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier:
            identifiers = [record['id'] for record in self._list_records(rtype, name, content)]
        else:
            identifiers = [identifier]

        response = {'success': 'noop'}
        for identifier_to_delete in identifiers:
            delete_key = self._determine_delete_key(identifier_to_delete, rtype)
            query_params = {'action': 'select', 'json': 'yes', delete_key: identifier_to_delete}

            try:
                response = self._get('/CMD_API_DNS_CONTROL', query_params)
            except requests.exceptions.HTTPError:
                response = {'success': 'Delete Failed'}

            LOGGER.debug('delete_record: %s', response)

        return response['success'].lower().find('deleted') > 0

    def _determine_delete_key(self, identifier, rtype):
        # The indicator for the record that needs to be removed is determined
        # by the type of the record and its index within all records of that
        # type. There's an additional check on the name and value which still
        # need to match for the removal to actually occur
        if not rtype:
            # An rtype is necessary to create the delete_key. However, it may
            # not be specified in which case an effort needs to be made to
            # figure it out automatically. The necessary data can be recreated
            # from the identifier
            identifier_parts = identifier.split('&')
            name = identifier_parts[0].split('=').pop()
            content = identifier_parts[1].split('=').pop()

            records = self.list_records(None, name, content)
            rtype = records[0]['type']

        existing_records = self.list_records(rtype)
        existing_record_index = 0
        for (index, record) in enumerate(existing_records):
            if record['id'] == identifier:
                existing_record_index = index

        return '{0}recs{1}'.format(rtype, existing_record_index).lower()

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        query_params['domain'] = self.domain

        response = requests.request(
            action, self.endpoint + url,
            auth=HTTPBasicAuth(
                self._get_provider_option('auth_username'),
                self._get_provider_option('auth_password')
            ),
            params=query_params
        )

        # If the request fails for any reason, throw an error
        response.raise_for_status()

        if 'json' in response.headers['Content-Type'].lower():
            return response.json()

        return response.text
