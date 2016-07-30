from base import Provider as BaseProvider
import requests
import json

def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify token used authenticate to DNS provider")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://api.vultr.com/v1'

    def authenticate(self):

        payload = self._get('/dns/list')

        if not [item for item in payload if item['domain'] == self.options['domain']]:
            raise StandardError('No domain found')

        self.domain_id = self.options['domain']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'type': type,
            'domain': self.domain_id,
            'name': self._relative_name(name),
            'priority': 0
        }
        if type == 'TXT':
            record['data'] = "\"{0}\"".format(content)
        else:
            record['data'] = content
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')
        payload = self._post('/dns/create_record', record)

        print 'create_record: {0}'.format(True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._get('/dns/records', {'domain': self.domain_id})
        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': "{0}.{1}".format(record['name'], self.domain_id),
                'ttl': record.get('ttl', self.options.get('ttl',self.default_ttl)),
                'content': record['data'],
                'id': record['RECORDID']
            }
            processed_record = self._clean_TXT_record(processed_record)
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
            'domain': self.domain_id,
            'RECORDID': identifier,
            'ttl': self.options.get('ttl',self.default_ttl)
        }
        # if type:
        #     data['type'] = type
        if name:
            data['name'] = self._relative_name(name)
        if content:
            if type == 'TXT':
                data['data'] = "\"{0}\"".format(content)
            else:
                data['data'] = content

        payload = self._post('/dns/update_record', data)

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

        data = {
            'domain': self.domain_id,
            'RECORDID': identifier
        }
        payload = self._post('/dns/delete_record', data)

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
            # 'Content-Type': 'application/json',
            'API-Key': self.options['auth_token']
        }

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=data,
                             headers=default_headers)
        r.raise_for_status()  # if the request fails for any reason, throw an error.

        if action == 'DELETE' or action == 'PUT' or action == 'POST':
            return r.text # vultr handles succss/failure via HTTP Codes, Only GET returns a response.
        return r.json()
