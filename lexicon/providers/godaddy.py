import logging
import requests
import json

from .base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.add_argument('--auth-key', help='specify the key to access the API')
    subparser.add_argument('--auth-secret', help='specify the secret to access the API')

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.godaddy.com/v1')

    def authenticate(self):
        domain = self.options.get('domain')

        result = self._get('/domains/{0}'.format(domain))
        self.domain_id = result['domainId']

    def list_records(self, type=None, name=None, content=None):
        domain = self.options.get('domain')

        url = '/domains/{0}/records'.format(domain)
        if type:
            url += '/{0}'.format(type)
        if name:
            url += '/{0}'.format(self._relative_name(name))

        raws = self._get(url)

        records = []
        for raw in raws:
            records.append({
                'type': raw['type'],
                'name': self._full_name(raw['name']),
                'ttl': raw['ttl'],
                'content': raw['data']
            })

        if content:
            records = [record for record in records if record['data'].lower() == content.lower()]

        LOGGER.debug('list_records: %s', records)

        return records

    def create_record(self, type, name, content):
        domain = self.options.get('domain')
        relative_name = self._relative_name(name)
        ttl = self.options.get('ttl')

        # Retrieve existing data for given type and name, and append a new record
        records = self._get('/domains/{0}/records/{1}/{2}'.format(domain, type, relative_name))

        data = {'data': content}
        if ttl:
            data['ttl'] = ttl

        records.append(data)

        # Synchronize data with inserted record into DNS zone for given type and name
        self._put('/domains/{0}/records/{1}/{2}'.format(domain, type, relative_name), records)

        LOGGER.debug('create_record: %s %s %s', type, name, content)

        return True

    def update_record(self, identifier, type=None, name=None, content=None):
        # No identifier is used with GoDaddy. 
        # We can rely only on type + name (which are then mandatory) to get the relevant records.
        # Furthermore, we cannot update all matching records, as it would lead to an error (two entries of same type + name cannot have the same content).
        # So we search first matching record for type + name on which content is different, and we update it before synchronizing the DNS zone.
        if not type:
            raise Exception('ERROR: type is required')
        if not name:
            raise Exception('ERROR: name is required')

        domain = self.options.get('domain')
        relative_name = self._relative_name(name)

        # Retrieve existing data for given type and name, and update matching records
        records = self._get('/domains/{0}/records/{1}/{2}'.format(domain, type, relative_name))

        for record in records:
            if record['type'].upper() == type.upper() and self._relative_name(record['name']).lower() == relative_name.lower() and record['data'] != content:
                record['data'] = content
                break
        
        # Synchronize data with updated records into DNS zone for given type and name
        self._put('/domains/{0}/records/{1}/{2}'.format(domain, type, relative_name), records)

        LOGGER.debug('update_record: %s %s %s', type, name, content)

        return True

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        # No identifier is used with GoDaddy. 
        # We can rely only on type + name (which are then mandatory) to know which records need to be deleted.
        if not type:
            raise Exception('ERROR: type is required')
        if not name:
            raise Exception('ERROR: name is required')

        domain = self.options.get('domain')
        relative_name = self._relative_name(name)

        # Retrieve existing data for given type and name, and filter out entries matching given content
        records = self._get('/domains/{0}/records/{1}/{2}'.format(domain, type, relative_name))
        filtered_records = [record for record in records if content and record['data'].lower() != content.lower()]

        # Synchronize data with expurged entries into DNS zone for given type and name
        self._put('/domains/{0}/records/{1}/{2}'.format(domain, type, relative_name), filtered_records)

        LOGGER.debug('delete_records: %s %s %s', type, name, content)

        return True

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if not data:
            data = {}
        if not query_params:
            query_params = {}

        result = requests.request(action, self.api_endpoint + url,
                                  params=query_params,
                                  data=json.dumps(data),
                                  headers={
                                      'Content-Type': 'application/json',
                                      'Accept': 'application/json',
                                      # GoDaddy use a key/secret pair to authenticate
                                      'Authorization': 'sso-key {0}:{1}'.format(
                                          self.options.get('auth_key'),
                                          self.options.get('auth_secret'))
                                  })

        result.raise_for_status()

        try:
            return result.json()
        except ValueError:
            # For some requests command (eg. PUT), GoDaddy will not return any json, just HTTP status
            return None
