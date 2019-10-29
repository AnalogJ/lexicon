"""Module provider for Dreamhost"""
from __future__ import absolute_import
import base64
import json
import logging
import time

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dreamhost.com']

_DATA_NON_EXIST_ERROR_LIST = [
    'no_record',
    'no_type',
    'no_value',
    'no_such_record',
    'no_such_type',
    'no_such_value',
    'no_such_zone',
]

_DATA_ALREADY_EXIST_ERROR_LIST = [
    'record_already_exists_not_editable',
    'record_already_exists_remove_first',
    'CNAME_already_on_record',
]


class NonExistError(Exception):
    """NonExistError"""


class AlreadyExistError(Exception):
    """AlreadyExistError"""


def provider_parser(subparser):
    """Module provider for Dreamhost"""
    subparser.add_argument(
        "--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):
    """Provider class for Dreamhost"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.dreamhost.com/'

    # Dreamhost provides no identifier for a record.
    # Furthermore, Dreamhost requires type, record, value to delete a record.
    # The record defined in lexicon is {type, name, content, id}
    # We use base64(json({'type', 'name', 'content'}))
    # as the identifier of Dreamhost record.
    @staticmethod
    def _identifier(dreamhost_record):
        id_struct = {
            'type': dreamhost_record['type'],
            'name': dreamhost_record['record'],
            'content': dreamhost_record['value'],
        }
        return base64.urlsafe_b64encode(json.dumps(id_struct).encode('utf-8')).decode('utf-8')

    # The information in identifier follows the record in lexicon.
    # Provider._record_to_dreamhost_record transfers to dreamhost-based record.
    @staticmethod
    def _id_to_dreamhost_record(identifier):
        record = json.loads(base64.urlsafe_b64decode(identifier.encode('utf-8')).decode('utf-8'))
        dreamhost_record = Provider._record_to_dreamhost_record(record)
        return dreamhost_record

    # The information in identifier follows the record in lexicon.
    # 'id' is added in the record.
    @staticmethod
    def _id_to_record(identifier):
        record = json.loads(base64.urlsafe_b64decode(identifier.encode('utf-8')).decode('utf-8'))
        record['id'] = identifier

        return record

    # Transferring lexicon-based record to Dreamhost-based record.
    @staticmethod
    def _record_to_dreamhost_record(record):
        dreamhost_record = {
            'type': record['type'],
            'record': record['name'],
            'value': record['content'],
        }
        return dreamhost_record

    def _authenticate(self):
        self.domain_id = None
        payload = self._get('domain-list_domains')
        data = payload.get('data', None)
        if data is None:
            raise Exception('Domain not found')

        for domain in data:
            if domain.get('domain', '') == self.domain:
                self.domain_id = self.domain
        if self.domain_id is None:
            raise Exception('Domain not found')

    def _create_record(self, rtype, name, content):
        name = self._full_name(name)

        try:
            self._get('dns-add_record', query_params={
                'record': name,
                'type': rtype,
                'value': content,
            })
        except AlreadyExistError:
            pass

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):

        payload = self._get('dns-list_records')

        resource_list = payload.get('data', None)
        if not isinstance(resource_list, list):
            raise Exception('unable to get records: %s' % payload)

        resource_list = [
            resource for resource in resource_list if resource['zone'] == self.domain]
        if rtype:
            resource_list = [
                resource for resource in resource_list if resource['type'] == rtype]
        if name:
            name = self._full_name(name)
            resource_list = [
                resource for resource in resource_list if resource['record'] == name]
        if content:
            resource_list = [
                resource for resource in resource_list if resource['value'] == content]

        processed_records = []
        for dreamhost_record in resource_list:
            processed_records.append({
                'id': Provider._identifier(dreamhost_record),
                'type': dreamhost_record['type'],
                'name': dreamhost_record['record'],
                'content': dreamhost_record['value'],
            })

        return processed_records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier:
            try:
                self._delete_record(identifier)
            except NonExistError:
                pass

        return self._create_record(rtype=rtype, name=name, content=content)

    # Delete existing records.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        to_deletes = []
        if identifier:
            record = Provider._id_to_record(identifier)
            to_deletes.append(record)
        else:
            records = self._list_records(rtype=rtype, name=name, content=content)
            to_deletes = records

        # for-loop to delete deletes.
        err = None
        for each in to_deletes:
            try:
                dreamhost_record = Provider._record_to_dreamhost_record(each)
                self._get('dns-remove_record', query_params=dreamhost_record)

            except Exception as exception:  # pylint: disable=broad-except
                err = exception

            # Sleeping for 1-second to avoid trigerring ddos protecting in case of looped requests
            time.sleep(1)

        if err is not None:
            raise err

        return True

    # Helpers
    def _request(self, action='GET', url='', data=None, query_params=None):
        if data is None:
            data = {}

        if query_params is None:
            query_params = {}

        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        query_params['key'] = self._get_provider_option('auth_token')
        query_params['format'] = 'json'
        if 'cmd' not in query_params:
            query_params['cmd'] = url

        response = requests.request(action, self.api_endpoint, params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers)

        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        result = response.json()
        if result.get('result', '') != 'success':
            err_msg = result.get('data', '')
            if err_msg in _DATA_NON_EXIST_ERROR_LIST:
                raise NonExistError('Dreamhost non-exist error: {0}'.format(result))
            if err_msg in _DATA_ALREADY_EXIST_ERROR_LIST:
                raise AlreadyExistError('Dreamhost already-exist error: {0}'.format(result))
            raise Exception('Dreamhost api error: {0}'.format(result))
        return result
