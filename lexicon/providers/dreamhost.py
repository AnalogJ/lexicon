"""Module provider for Dreamhost"""
from __future__ import absolute_import
import json
import logging
import time

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dreamhost.com']


def provider_parser(subparser):
    """Module provider for Linode"""
    subparser.add_argument(
        "--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):
    """Provider class for Linode"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.dreamhost.com/'

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
        payload = self._get('dns-add_record', query_params={
            'record': name,
            'type': rtype,
            'value': content,
        })

        if (payload.get('result', '') != 'success' and
                payload.get('data', '') != 'record_already_exists_remove_first' and
                payload.get('data', '') != 'record_already_exists_not_editable'):
            raise Exception('unable to add record: %s' % payload)

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):

        payload = self._get('dns-list_records')

        if payload.get('result', '') != 'success':
            raise Exception('unable to get records: %s' % payload)

        resource_list = payload.get('data', None)
        if resource_list is None:
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
        for resource in resource_list:
            processed_records.append({
                'id': resource['type'] + '|' + resource['record'] + '|' + resource['value'],
                'type': resource['type'],
                'name': resource['record'],
                'content': resource['value'],
            })

        return processed_records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier == '':
            identifier = None
        if identifier is not None:
            id_list = identifier.split('|')
            if len(id_list) != 3:
                raise Exception('invalid identifier: %s' % (identifier))

            id_type, id_name, id_content = id_list

            try:
                self._delete_record(rtype=id_type, name=id_name, content=id_content)
            except:  # pylint: disable=bare-except
                pass

        return self._create_record(rtype=rtype, name=name, content=content)

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):

        id_type = None
        id_name = None
        id_content = None
        if identifier is not None:
            id_list = identifier.split('|')
            if len(id_list) != 3:
                raise Exception('invalid identifier: %s' % (identifier))

            id_type, id_name, id_content = id_list

        if rtype is None:
            rtype = id_type
        if name is None:
            name = id_name
        if content is None:
            content = id_content

        if name is not None:
            name = self._full_name(name)

        to_deletes = []
        if rtype is None or name is None or content is None:
            if identifier is None:
                records = self._list_records(rtype=rtype, name=name, content=content)
                to_deletes = records
        else:
            to_deletes = [{'record': name, "type": rtype, "value": content}]

        for each in to_deletes:
            try:
                self._get('dns-remove_record', query_params=each)
            except:  # pylint: disable=bare-except
                pass

        return True

    # Helpers
    def _request(self, action='GET', url='', data=None, query_params=None):
        time.sleep(1)
        if data is None:
            data = {}

        if query_params is None:
            query_params = {}

        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        query_params['api_key'] = self._get_provider_option('auth_token')
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
            raise Exception('Dreamhost api error: {0}'.format(result))
        return result
