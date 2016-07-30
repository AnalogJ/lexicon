from base import Provider as BaseProvider
import requests
import json

def ProviderParser(subparser):
    subparser.add_argument("--auth-domaintoken", help="specify domain token to authenticate")
    subparser.add_argument("--auth-username", help="specify email address used to authenticate")
    subparser.add_argument("--auth-password", help="specify password used to authenticate")
    subparser.add_argument("--auth-token", help="specify simple api token used authenticate")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://api.dnsimple.com/v1'

    def authenticate(self):

        payload = self._get('/domains/{0}'.format(self.options['domain']))

        if not payload['domain']:
            raise StandardError('No domain found')

        self.domain_id = self.options['domain']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {'record':
                    {
                        'record_type': type,
                        'name': self._relative_name(name),
                        'content': content
                    }
                }
        if self.options.get('ttl'):
            record['record']['ttl'] = self.options.get('ttl')
        payload = {}
        try:
            payload = self._post('/domains/{0}/records'.format(self.domain_id), record)
        except requests.exceptions.HTTPError, e:
            if e.response.status_code == 400:
                payload = {'record': {}}

            # http 400 is ok here, because the record probably already exists
        print 'create_record: {0}'.format('record' in payload)
        return 'record' in payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}
        if type:
            filter['type'] = type
        if name:
            filter['name'] = self._relative_name(name)
        payload = self._get('/domains/{0}/records'.format(self.domain_id), filter)

        records = []
        for record in payload:
            processed_record = {
                'type': record['record']['record_type'],
                'name': '{0}.{1}'.format(record['record']['name'],self.options['domain']),
                'ttl': record['record']['ttl'],
                'content': record['record']['content'],
                'id': record['record']['id']
            }
            records.append(processed_record)

        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {'record': {}}

        if name:
            data['record']['name'] = self._relative_name(name)
        if content:
            data['record']['content'] = content
        if self.options.get('ttl'):
            data['record']['ttl'] = self.options.get('ttl')

        payload = self._put('/domains/{0}/records/{1}'.format(self.domain_id, identifier), data)

        print 'update_record: {0}'.format('record' in payload)
        return 'record' in payload

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
        payload = self._delete('/domains/{0}/records/{1}'.format(self.domain_id, identifier))

        # is always True at this point, if a non 200 response is returned an error is raised.
        print 'delete_record: {0}'.format(True)
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        default_auth = None

        if self.options.get('auth_domaintoken'):
            default_headers['X-DNSimple-Domain-Token'] = self.options.get('auth_domaintoken')

        elif self.options.get('auth_username') and self.options.get('auth_token'):
            default_headers['X-DNSimple-Token'] = "{0}:{1}".format(self.options['auth_username'],self.options['auth_token'])

        elif self.options.get('auth_username') and self.options.get('auth_password'):
            default_auth=(self.options['auth_username'], self.options['auth_password'])



        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
