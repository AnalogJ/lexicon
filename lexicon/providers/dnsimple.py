from base import BaseProvider
import requests
import json
class Provider(BaseProvider):

    def __init__(self, options):
        super(Provider, self).__init__(options)
        self.domain_name = None
        self.api_endpoint = 'https://api.dnsimple.com/v1'

    def authenticate(self):

        payload = self._get('/domains/{0}'.format(self.options.domain))

        if not payload['domain']:
            raise StandardError('No domain found')

        self.domain_name = self.options.domain


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        name =  name.rstrip(self.domain_name) + '.' + self.options.subdomain.rstrip('.')

        record = {'record':
                    {
                        'record_type': type,
                        'name': name,
                        'content': content
                    }
                }
        try:
            payload = self._post('/domains/{0}/records'.format(self.domain_name), record)
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
            filter['name'] = name.rstrip('.') # strip trailing period

        payload = self._get('/domains/{0}/records'.format(self.domain_name), filter)

        records = []
        for record in payload:
            processed_record = {
                'type': record['record']['record_type'],
                'name': record['record']['name'],
                'ttl': record['record']['ttl'],
                'content': record['record']['content'],
                'id': record['record']['id']
            }
            records.append(processed_record)

        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        name =  name.rstrip(self.domain_name) + '.' + self.options.subdomain.rstrip('.')
        data = {'record': {}}

        if name:
            data['record']['name'] = name
        if content:
            data['record']['content'] = content

        payload = self._put('/domains/{0}/records/{1}'.format(self.domain_name, identifier), data)

        print 'update_record: {0}'.format('record' in payload)
        return 'record' in payload

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        name =  name.rstrip(self.domain_name) + '.' + self.options.subdomain.rstrip('.')
        if not identifier:
            records = self.list_records(type, name, content)
            print records
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise StandardError('Record identifier could not be found.')
        payload = self._delete('/domains/{0}/records/{1}'.format(self.domain_name, identifier))

        # is always True at this point, if a non 200 response is returned an error is raised.
        print 'delete_record: {0}'.format(True)
        return True


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

        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        default_auth = None
        if self.options.auth_username and self.options.auth_token:
            default_headers['X-DNSimple-Token'] = "{0}:{1}".format(self.options.auth_username,self.options.auth_token)

        if self.options.auth_username and self.options.auth_password:
            default_auth=(self.options.auth_username, self.options.auth_password)



        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
