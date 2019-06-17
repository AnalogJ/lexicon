"""Module provider for DirectAdmin hosts"""
import logging
import requests
import warnings

from lexicon.providers.base import Provider as BaseProvider
from requests.auth import HTTPBasicAuth

LOGGER = logging.getLogger(__name__)

def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument(
        "--auth-password",
        help = "specify password for authentication (or login key in case of two-factor-authentication)"
    )

    subparser.add_argument(
        "--auth-username",
        help = "specify username for authentication"
    )

    subparser.add_argument(
        "--endpoint",
        help = "specify the DirectAdmin endpoint"
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
            response = self._get()
        except requests.exceptions.HTTPError as err:
            # A 401 error will be returned in case of incorrect or missing
            # credentials
            cause = err.response.json()['error']
            raise Exception(cause)

    def _create_record(self, rtype, name, content):
        query_params = {
            'action': 'add', 'name': name, 'type': rtype, 'value': content
        }

        if self._get_lexicon_option('ttl'):
            query_params['ttl'] = self._get_lexicon_option('ttl')

        try:
            response = self._get('/', query_params)
        except requests.exceptions.HTTPError:
            response = { 'success': False }

        LOGGER.debug('create_record: %s', response)

        return response['success'].lower().find('added') >= 0

    def _list_records(self, rtype=None, name=None, content=None):
        response = { 'records': [] }
        try:
            response = self._get()
        except requests.exceptions.HTTPError as err:
            print(err.response.text)
            raise

        records = response['records']
        if rtype:
            records = [ record for record in records if record['type'] == rtype ]
        if name:
            cmp_name = self._relative_name(name.lower())
            records = [ record for record in records if record['name'] == cmp_name ]
        if content:
            records = [ record for record in records if record['value'] == content ]

        records = [ self._parse_response_record(record) for record in records ]

        LOGGER.debug('list_records: %s', records)

        return records

    def _parse_response_record(self, response_record):
        # Most fields in a record response match, except for content which is
        # value
        return {
            'content': response_record['value'],
            'name': response_record['name'],
            'ttl': response_record['ttl'],
            'type': response_record['type']
        }

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # Editing a record is a combination of removing the old record and
        # adding a new one, but specifying 'edit' as the action while passing
        # all parameters necessary for both deletion and creation

        # The original value of record to edit is necessary to be able to
        # create the appropriate delete payload
        original_records = self.list_records(rtype, name)
        if len(original_records) > 1:
            warnings.warn('Found multiple records to edited. Cannot continue...')
            return False
        original_content = original_records[0]['content']

        delete_key, delete_value = self._build_delete_payload(rtype, name, original_content)

        query_params = {
            'action': 'edit',
            delete_key: delete_value,
            'name': name, 'type': rtype, 'value': content
        }

        try:
            response = self._get('/', query_params)
        except requests.exceptions.HTTPError:
            response = { 'success': False }

        LOGGER.debug('update_record: %s', response)

        return response['success'].lower().find('added') > 0

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_key, delete_value = self._build_delete_payload(rtype, name, content)
        query_params = { 'action': 'select', delete_key: delete_value }

        try:
            response = self._get('/', query_params)
        except requests.exceptions.HTTPError:
            response = { 'success': False }

        LOGGER.debug('delete_record: %s', response)

        return response['success'].lower().find('deleted') > 0

    def _build_delete_payload(self, rtype=None, name=None, content=None):
        # If the content contains spaces, the value needs to be wrapped in
        # quotes. This needs to happen first as the result is used to find the
        # index of the existing record below. However, be sure to not requote
        # already quoted values
        if content is None:
            content = ''
        if content.find(' ') > 0 and content[0] != '"':
            content = '"{0}"'.format(content)

        # The indicator for the record that needs to be removed is determined
        # by the type of the record and its index within all records of that
        # type. There's an additional check on the name and value which still
        # need to match for the removal to actually occur
        existing_records = self.list_records(rtype)
        existing_record_index = 0
        cmp_name = self._relative_name(name.lower())
        for (index, record) in enumerate(existing_records):
            if record['name'] == cmp_name and record['content'] == content:
                existing_record_index = index

        selecttype = '{0}recs{1}'.format(rtype, existing_record_index).lower()
        value = 'name={0}&value={1}'.format(name, content)

        return selecttype, value

    def _request(self, action='GET', url='/', data={}, query_params={}):
        if query_params is None:
            query_params = {}

        query_params['domain'] = self.domain
        query_params['json'] = 'yes'

        response = requests.request(
            action, self.endpoint + '/CMD_API_DNS_CONTROL',
            auth=HTTPBasicAuth(
                self._get_provider_option('auth_username'),
                self._get_provider_option('auth_password')
            ),
            params=query_params
        )

        # If the request fails for any reason, throw an error
        response.raise_for_status()

        return response.json()
