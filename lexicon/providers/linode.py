from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

import lexicon.common.exceptions as lexceptions
from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify api key used authenticate to DNS provider")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.linode.com/api/')

    def authenticate(self):
        self.domain_id = None
        payload = self._get('domain.list')
        for domain in payload['DATA']:
            if domain['DOMAIN'] == self.options['domain']:
                self.domain_id = domain['DOMAINID']
        if self.domain_id == None:
            raise lexceptions.DomainNotFoundError()

    def create_record(self, type, name, content, options=None):
        if len(self.list_records(type, name, content)) == 0:
            self._get('domain.resource.create', query_params={
                'DomainID': self.domain_id,
                'Name': self._relative_name(name),
                'Type': type,
                'Target': content,
                'TTL_sec': options['ttl'] if options and 'ttl' in options else 0
            })

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        payload = self._get('domain.resource.list', query_params={ 'DomainID': self.domain_id })
        resource_list = payload['DATA']
        if type:
            resource_list = [resource for resource in resource_list if resource['TYPE'] == type]
        if name:
            cmp_name = self._relative_name(name.lower())
            resource_list = [resource for resource in resource_list if resource['NAME'] == cmp_name]
        if content:
            resource_list = [resource for resource in resource_list if resource['TARGET'] == content]
        
        processed_records = []
        for resource in resource_list:
            processed_records.append({
                'id': resource['RESOURCEID'],
                'type': resource['TYPE'],
                'name': self._full_name(resource['NAME']),
                'ttl': resource['TTL_SEC'],
                'content': resource['TARGET']
            })
        logger.debug('list_records: %s', processed_records)
        return processed_records
    
    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content_old=None, content=None, options=None):
        if not identifier:
            resources = self.list_records(type, name, content_old)
            identifier = resources[0]['id'] if len(resources) > 0 else None
            if not identifier:
                raise lexceptions.RecordNotFoundError()
        elif identifier and name and (not content or content_old == content):
            # Reject name updates
            return False

        logger.debug('update_record: %s', identifier)
        
        query_params={
            'DomainID': self.domain_id,
            'ResourceID': identifier,
            'Target': content
        }
        if options and 'ttl' in options:
            query_params['TTL_sec'] = options['ttl']
        self._get('domain.resource.update', query_params=query_params)
        
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
        
        logger.debug('delete_records: %s', delete_resource_id)
        
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
        
        query_params['api_key'] = self.options.get('auth_token')
        query_params['resultFormat'] = 'JSON'
        query_params['api_action'] = url
        
        r = requests.request(action, self.api_endpoint, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        if action == 'DELETE':
            return ''
        else:
            result = r.json()
            if len(result['ERRORARRAY']) > 0:
                raise Exception('Linode api error: {0}'.format(result['ERRORARRAY']))
            return result

