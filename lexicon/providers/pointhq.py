from base import Provider as BaseProvider
import requests
import json
class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://pointhq.com'

    def authenticate(self):

        payload = self._get('/zones', {
            'zone': {
                'name': self.options['domain']
            }
        })

        if not payload['zone']:
            raise StandardError('No domain found')

        self.domain_id = payload['zone']['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        payload = self._post('/zones/{0}/records'.format(self.domain_id), {'zone_record': {'record_type': type, 'name': name, 'data': content}})

        print 'create_record: {0}'.format(payload['zone_record'])
        return bool(payload['zone_record'])

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}
        if type:
            filter['record_type'] = type
        if name:
            filter['name'] = name.rstrip('.') # strip trailing period
        if content:
            filter['data'] = content

        payload = self._get('/zones/{0}/records'.format(self.domain_id), filter)

        records = []
        for record in payload:
            processed_record = {
                'type': record['zone_record']['record_type'],
                'name': record['zone_record']['name'],
                'ttl': record['zone_record']['ttl'],
                'content': record['zone_record']['data'],
                'id': record['zone_record']['id']
            }
            records.append(processed_record)

        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {}
        if type:
            data['record_type'] = type
        if name:
            data['name'] = name
        if content:
            data['data'] = content

        payload = self._put('/zones/{0}/records/{1}'.format(self.domain_id, identifier), {'zone_record': data})

        print 'update_record: {0}'.format(payload)
        return bool(payload['zone_record'])

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

        print 'delete_record: {0}'.format(payload['zone_record']['status'])
        return payload['zone_record']['status'] == 'OK'


    # Helpers
    def _get(self, url='/', query_params={}):
        return self._request('GET', url, query_params=query_params)

    def _post(self, url='/', data={}, query_params={}):
        return self._request('POST', url, data=data, query_params=query_params)

    def _put(self, url='/', data={}, query_params={}):
        return self._request('PUT', url, data=data, query_params=query_params)

    def _delete(self, url='/', query_params={}):
        return self._request('DELETE', url, query_params=query_params)

    def _request(self, action='GET',  url='/', data={}, query_params={}):
        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             auth=requests.auth.HTTPBasicAuth(self.options['auth_username'], self.options.get('auth_password') or self.options.get('auth_token')),
                             headers={
                                 'Content-Type': 'application/json',
                                 'Accept': 'application/json'
                             })
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()