from base import Provider as BaseProvider
import requests
import json

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://rage4.com/rapi'

    def authenticate(self):

        payload = self._get('/getdomainbyname/', {'name': self.options['domain']})

        if not payload['id']:
            raise StandardError('No domain found')

        self.domain_id = payload['id']

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'id': self.domain_id,
            'name': self._clean_name(name),
            'content': content,
            'type': type
        }
        payload = {}
        try:
            payload = self._post('/createrecord/',{},record)
        except requests.exceptions.HTTPError, e:
            if e.response.status_code == 400:
                payload = {}

                # http 400 is ok here, because the record probably already exists
        print 'create_record: {0}'.format(payload['status'])
        return payload['status']

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {
            'id': self.domain_id
        }
        if name:
            filter['name'] = self._clean_name(name)
        payload = self._get('/getrecords/', filter)

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': record['name'],
                'ttl': record['ttl'],
                'content': record['content'],
                'id': record['id']
            }
            records.append(processed_record)


        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'id': identifier
        }

        if name:
            data['name'] = self._clean_name(name)
        if content:
            data['content'] = content
        # if type:
        #     raise 'Type updating is not supported by this provider.'

        payload = self._put('/updaterecord/', {}, data)

        print 'update_record: {0}'.format(payload['status'])
        return payload['status']

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
        payload = self._post('/deleterecord/', {'id': identifier})

        # is always True at this point, if a non 200 response is returned an error is raised.
        print 'delete_record: {0}'.format(payload['status'])
        return payload['status']


    # Helpers

    # record names can be in a variety of formats: relative (sub), full (sub.example.com), and fqdn (sub.example.com.)
    # Rage4 handles full record names, so we need to make sure we clean up all user specified record_names before
    # submitting them
    def _clean_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if not record_name.endswith(self.options['domain']):
            record_name = "{0}.{1}".format(record_name, self.options['domain'])
        return record_name

    def _get(self, url='/', query_params={}):
        return self._request('GET', url, query_params=query_params)

    def _post(self, url='/', data={}, query_params={}):
        return self._request('POST', url, data=data, query_params=query_params)

    def _put(self, url='/', data={}, query_params={}):
        return self._request('PUT', url, data=data, query_params=query_params)

    def _delete(self, url='/', query_params={}):
        return self._request('DELETE', url, query_params=query_params)

    def _request(self, action='GET',  url='/', data={}, query_params={}):

        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        default_auth = requests.auth.HTTPBasicAuth(self.options['auth_username'], self.options['auth_token'])

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
