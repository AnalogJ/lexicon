from base import Provider as BaseProvider
import requests
import json

def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify email address used to authenticate")
    subparser.add_argument("--auth-token", help="specify token used authenticate")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://api.luadns.com/v1'

    def authenticate(self):

        payload = self._get('/zones')

        domain_info = next((domain for domain in payload if domain['name'] == self.options['domain']), None)

        if not domain_info:
            raise StandardError('No domain found')

        self.domain_id = domain_info['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        payload = self._post('/zones/{0}/records'.format(self.domain_id), {'type': type, 'name': self._fqdn_name(name), 'content': content, 'ttl': self.options.get('ttl',self.default_ttl)})

        print 'create_record: {0}'.format(True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        payload = self._get('/zones/{0}/records'.format(self.domain_id))

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': self._full_name(record['name']),
                'ttl': record['ttl'],
                'content': record['content'],
                'id': record['id']
            }
            records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'] == content]

        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'ttl': self.options.get('ttl',self.default_ttl)
        }
        if type:
            data['type'] = type
        if name:
            data['name'] = self._fqdn_name(name)
        if content:
            data['content'] = content


        payload = self._put('/zones/{0}/records/{1}'.format(self.domain_id, identifier), data)

        print 'update_record: {0}'.format(True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            print records
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise StandardError('Record identifier could not be found.')
        payload = self._delete('/zones/{0}/records/{1}'.format(self.domain_id, identifier))

        print 'delete_record: {0}'.format(True)
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             auth=requests.auth.HTTPBasicAuth(self.options['auth_username'], self.options['auth_token']),
                             headers={
                                 'Content-Type': 'application/json',
                                 'Accept': 'application/json'
                             })
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()