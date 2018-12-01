from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['linode.com']


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.linode.com/api/'

    def authenticate(self):
        self.domain_id = None
        payload = self._get('domain.list')
        for domain in payload['DATA']:
            if domain['DOMAIN'] == self.domain:
                self.domain_id = domain['DOMAINID']
        if self.domain_id is None:
            raise Exception('Domain not found')

    def create_record(self, type, name, content):
        if len(self.list_records(type, name, content)) == 0:
            self._get('domain.resource.create', query_params={
                'DomainID': self.domain_id,
                'Name': self._relative_name(name),
                'Type': type,
                'Target': content,
                'TTL_sec': 0
            })

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        payload = self._get('domain.resource.list', query_params={
                            'DomainID': self.domain_id})
        resource_list = payload['DATA']
        if type:
            resource_list = [
                resource for resource in resource_list if resource['TYPE'] == type]
        if name:
            cmp_name = self._relative_name(name.lower())
            resource_list = [
                resource for resource in resource_list if resource['NAME'] == cmp_name]
        if content:
            resource_list = [
                resource for resource in resource_list if resource['TARGET'] == content]

        processed_records = []
        for resource in resource_list:
            processed_records.append({
                'id': resource['RESOURCEID'],
                'type': resource['TYPE'],
                'name': self._full_name(resource['NAME']),
                'ttl': resource['TTL_SEC'],
                'content': resource['TARGET']
            })
        LOGGER.debug('list_records: %s', processed_records)
        return processed_records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        if not identifier:
            resources = self.list_records(type, name, None)
            identifier = resources[0]['id'] if len(resources) > 0 else None

        LOGGER.debug('update_record: %s', identifier)

        self._get('domain.resource.update', query_params={
            'DomainID': self.domain_id,
            'ResourceID': identifier,
            'Name': self._relative_name(name).lower() if name else None,
            'Type': type if type else None,
            'Target': content if content else None
        })

        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        delete_resource_id = []
        if not identifier:
            resources = self.list_records(type, name, content)
            delete_resource_id = [resource['id'] for resource in resources]
        else:
            delete_resource_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_resource_id)

        for resource_id in delete_resource_id:
            self._get('domain.resource.delete', query_params={
                'DomainID': self.domain_id,
                'ResourceID': resource_id
            })

        return True

    # Helpers
    def _request(self, action='GET',  url='', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        query_params['api_key'] = self._get_provider_option('auth_token')
        query_params['resultFormat'] = 'JSON'
        query_params['api_action'] = url

        r = requests.request(action, self.api_endpoint, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        if action == 'DELETE':
            return ''
        else:
            result = r.json()
            if len(result['ERRORARRAY']) > 0:
                raise Exception(
                    'Linode api error: {0}'.format(result['ERRORARRAY']))
            return result
