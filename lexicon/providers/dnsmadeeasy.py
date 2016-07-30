from __future__ import print_function
from __future__ import absolute_import
from .base import Provider as BaseProvider
from builtins import bytes
import requests
import json
import datetime
import locale
import contextlib
from hashlib import sha1
import hmac

def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify username used to authenticate")
    subparser.add_argument("--auth-token", help="specify token used authenticate=")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://api.dnsmadeeasy.com/V2.0'

    def authenticate(self):

        payload = self._get('/dns/managed/name', {'domainname': self.options['domain']})

        if not payload['id']:
            raise Exception('No domain found')

        self.domain_id = payload['id']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'type': type,
            'name': self._relative_name(name),
            'value': content,
            'ttl': 86400
        }
        payload = {}
        try:
            payload = self._post('/dns/managed/{0}/records/'.format(self.domain_id), record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                payload = {}

                # http 400 is ok here, because the record probably already exists
        print('create_record: {0}'.format('name' in payload))
        return 'name' in payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}
        if type:
            filter['type'] = type
        if name:
            filter['recordName'] = self._relative_name(name)
        payload = self._get('/dns/managed/{0}/records'.format(self.domain_id), filter)

        records = []
        for record in payload['data']:
            processed_record = {
                'type': record['type'],
                'name': '{0}.{1}'.format(record['name'], self.options['domain']),
                'ttl': record['ttl'],
                'content': record['value'],
                'id': record['id']
            }

            processed_record = self._clean_TXT_record(processed_record)
            records.append(processed_record)

        print('list_records: {0}'.format(records))
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'id': identifier,
            'ttl': 86400
        }

        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['value'] = content
        if type:
            data['type'] = type

        payload = self._put('/dns/managed/{0}/records/{1}'.format(self.domain_id, identifier), data)

        print('update_record: {0}'.format(True))
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            print(records)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')
        payload = self._delete('/dns/managed/{0}/records/{1}'.format(self.domain_id, identifier))

        # is always True at this point, if a non 200 response is returned an error is raised.
        print('delete_record: {0}'.format(True))
        return True


    # Helpers

    # this method allows you to set the locale when doing datetime string formatting.
    # https://stackoverflow.com/questions/18593661/how-do-i-strftime-a-date-object-in-a-different-locale
    @contextlib.contextmanager
    def setlocale(self, *args, **kw):
        saved = locale.setlocale(locale.LC_ALL)
        #yield locale.setlocale(*args, **kw)
        yield locale.setlocale(locale.LC_TIME, 'en_US.UTF-8')
        locale.setlocale(locale.LC_ALL, saved)

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'x-dnsme-apiKey': self.options['auth_username']
        }
        default_auth = None

        # all requests require a HMAC header and timestamp header.
        now = datetime.datetime.utcnow()
        # required format: Sat, 12 Feb 2011 20:59:04 GMT
        with self.setlocale(locale.LC_TIME, 'en_US.utf8'):
            request_date = now.strftime('%a, %d %b %Y %H:%M:%S GMT')
            hashed = hmac.new(bytes(self.options['auth_token'], 'ascii'), 
                              bytes(request_date, 'ascii'), sha1)

            default_headers['x-dnsme-requestDate'] = request_date
            default_headers['x-dnsme-hmac'] = hashed.hexdigest()

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.

        # PUT and DELETE actions dont return valid json.
        if action == 'DELETE' or action == 'PUT':
            return r.text
        return r.json()
