"""Module provider for Linode V4"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['linode.com']


def provider_parser(subparser):
    """Configure provider parser for Linode V4"""
    subparser.add_argument(
        "--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):
    """Provider class for Linode V4"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.linode.com/v4/'

    def _authenticate(self):
        self.domain_id = None
        payload = self._get('domains', query_params={
            'filter': {
                'domain': self.domain
            }
        })
        if payload['data']:
            self.domain_id = payload['data'][0]['id']
        if self.domain_id is None:
            raise Exception('Domain not found')

    def _create_record(self, rtype, name, content):
        if not self._list_records(rtype, name, content):
            if name:
                name = self._relative_name(name)

            self._post('domains/{0}/records'.format(self.domain_id), data={
                'name': name,
                'type': rtype,
                'target': content,
                'ttl_sec': 0
            })

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        resources_url = "domains/{0}/records".format(self.domain_id)

        if name:
            name = self._relative_name(name)

        processed_records = []

        payload = self._get(resources_url)
        for page in range(1, payload['pages'] + 1, 1):
            if page > 1:
                payload = self._get(resources_url, query_params={
                    'page': page
                })

            resource_list = payload['data']
            if rtype:
                resource_list = [
                    resource for resource in resource_list if resource['type'] == rtype]
            if name:
                resource_list = [resource for resource in resource_list if self._relative_name(
                    resource['name']) == name]
            if content:
                resource_list = [
                    resource for resource in resource_list if resource['target'] == content]

            for resource in resource_list:
                processed_records.append({
                    'id': resource['id'],
                    'type': resource['type'],
                    'name': self._full_name(resource['name']),
                    'ttl': resource['ttl_sec'],
                    'content': resource['target']
                })

        LOGGER.debug('list_records: %s', processed_records)
        return processed_records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier:
            resources = self._list_records(rtype, name, None)
            identifier = resources[0]['id'] if resources else None

        LOGGER.debug('update_record: %s', identifier)

        if name:
            name = self._relative_name(name)

        url = 'domains/{0}/records/{1}'.format(self.domain_id, identifier)
        self._put(url, data={
            'name': name.lower() if name else None,
            'type': rtype if rtype else None,
            'target': content if content else None
        })

        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_resource_id = []
        if not identifier:
            resources = self._list_records(rtype, name, content)
            delete_resource_id = [resource['id'] for resource in resources]
        else:
            delete_resource_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_resource_id)

        for resource_id in delete_resource_id:
            self._delete('domains/{0}/records/{1}'.format(
                self.domain_id,
                resource_id
            ))

        return True

    # Helpers
    def _request(self, action='GET', url='', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(self._get_provider_option('auth_token'))
        }

        request_filter = query_params['filter'] if 'filter' in query_params else None
        if request_filter is not None:
            default_headers['X-Filter'] = json.dumps(request_filter)
            del query_params['filter']

        request_url = "{0}{1}".format(self.api_endpoint, url)

        response = requests.request(action, request_url, params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers)
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if action == 'DELETE':
            return ''
        result = response.json()
        return result
