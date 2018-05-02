from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify api key used authenticate to DNS provider")

class Provider(BaseProvider):
    
    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.linode.com/v4/')

    def authenticate(self):
        self.domain_id = None
        payload = self._get('domains', query_params={
            'filter': {
                'domain': self.options['domain']
            }
        })
        if len(payload['data']) > 0:
            self.domain_id = payload['data'][0]['id']
        if self.domain_id == None:
            raise Exception('Domain not found')

    def create_record(self, type, name, content):
        if len(self.list_records(type, name, content)) == 0:
            if name:
                name = self._relative_name(name)
            
            self._post('domains/{0}/records'.format(self.domain_id), data={
                'name': name,
                'type': type,
                'target': content,
                'ttl_sec': 0
            })

        return True
    
    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
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
            if type:
                resource_list = [resource for resource in resource_list if resource['type'] == type]
            if name:
                resource_list = [resource for resource in resource_list if self._relative_name(resource['name']) == name]
            if content:
                resource_list = [resource for resource in resource_list if resource['target'] == content]
            
            for resource in resource_list:
                processed_records.append({
                    'id': resource['id'],
                    'type': resource['type'],
                    'name': self._full_name(resource['name']),
                    'ttl': resource['ttl_sec'],
                    'content': resource['target']
                })
        
        logger.debug('list_records: %s', processed_records)
        return processed_records
    
    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        if not identifier:
            resources = self.list_records(type, name, None)
            identifier = resources[0]['id'] if len(resources) > 0 else None
        
        logger.debug('update_record: %s', identifier)
        
        if name:
            name = self._relative_name(name)
        
        url = 'domains/{0}/records/{1}'.format(self.domain_id, identifier)
        self._put(url, data={
            'name': name.lower() if name else None,
            'type': type if type else None,
            'target': content if content else None
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
        
        logger.debug('delete_records: %s', delete_resource_id)
        
        for resource_id in delete_resource_id:
            self._delete('domains/{0}/records/{1}'.format(
                self.domain_id,
                resource_id
            ))
        
        return True

    # Helpers
    def _request(self, action='GET',  url='', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(self.options.get('auth_token'))
        }
        
        request_filter = query_params['filter'] if 'filter' in query_params else None
        if request_filter is not None:
            default_headers['X-Filter'] = json.dumps(request_filter)
            del query_params['filter']
        
        request_url = "{0}{1}".format(self.api_endpoint, url)
        
        r = requests.request(action, request_url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        if action == 'DELETE':
            return ''
        else:
            result = r.json()
            return result

