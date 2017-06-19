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

    def create_record(self, type, name, content):
        domain = self.options.get('domain')
        ttl = self.options.get('ttl')

        data = {'data': content}
        if ttl:
            data['ttl'] = ttl

        self._put('/domains/{0}/records/{1}/{2}'
                  .format(domain, type, self._relative_name(name)), [data])

        LOGGER.debug('create_record: %s %s %s', type, name, content)

        return True

    def list_records(self, type=None, name=None, content=None):
        domain = self.options.get('domain')
        records = []

        url = '/domains/{0}/records'.format(domain)
        if type:
            url += '/{0}'.format(type)
        if name:
            url += '/{0}'.format(self._relative_name(name))

        raws = self._get(url)

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

    def update_record(self, identifier, type=None, name=None, content=None):
        # With GoDaddy API, creating a record for given type and name is the same
        #   than updating the record.
        return self.create_record(type, name, content)

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        domain = self.options.get('domain')

        if not type:
            raise Exception('ERROR: type is required')
        if not name:
            raise Exception('ERROR: name is required')
        if not content:
            raise Exception('ERROR: content is required')

        # OK some explanations need to be done here.
        # GoDaddy DNS API does not provide a direct way to delete a record (weird).
        # However it provides a way to get and update all records of a zone.
        # So :
        #  - we get all the records,
        #  - we filter the array to remove the record to be deleted,
        #  - then we push back the filtered array to set the zone without the record to be deleted.
        # And yes, we could limit the operation to a given type record (eg. TXT, there is an URL
        #   for that), but GoDaddy refuses to push back an empty set of a given type (yep, you
        #   cannot remove all your TXT with this URL, ultra weird).
        # It is likely to happen during a DNS challenge, as all TXT should be removed at the end.
        # So operating on all the zone avoid empty sets (there will always at least NS entries).
        records = self._get('/domains/{0}/records'.format(domain))
        to_insert = [record for record in records
                     if record['type'].lower() != type.lower()
                     or record['name'].lower() != self._relative_name(name).lower()
                     or record['data'].lower() != content.lower()]

        num_to_delete = len(records) - len(to_insert)

        if num_to_delete > 1:
            raise Exception('ERROR: multiple records marked to be deleted')

        self._put('/domains/{0}/records'.format(domain), to_insert)

        LOGGER.debug('delete_record: %s', num_to_delete != 0)

        return num_to_delete != 0

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
        return result.json()
