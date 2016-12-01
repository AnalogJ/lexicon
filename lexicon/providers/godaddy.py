from base import Provider as BaseProvider
import requests
import json

def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify ACCESS_KEY used to authenticate")
    subparser.add_argument("--auth-token", help="specify ACCESS_SECRET used authenticate")
    subparser.add_argument("--auth-access-key", help="specify ACCESS_KEY used to authenticate")
    subparser.add_argument("--auth-access-secret", help="specify ACCESS_SECRET used authenticate")
    subparser.add_argument("--shopper-id", help="optional shopper ID if reseller")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://api.godaddy.com/v1'

    # Don't authenticate. Your key and secret give you full access.
    # The key and secret are the person with the account and so can control
    # resources of the account that created the developer api key. This
    # includes reseller resources.
    def authenticate(self):
        pass

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = [{
            'type': str(type).capitalize(),
            'name': self._relative_name(name),
            'data': content,
        }]
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')

        payload = self._request('PATCH', self._domain_record_path(), record)
        print 'create_record: {0}'.format(payload)
        return payload['code'] if payload['code'] else True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        payload, records = self._list_records(type, name, content)
        print 'list_records: {0}'.format(records)
        return payload['code'] if payload['code'] else True

    # Update a record. Identifier must be specified.
    # Identifier is ignored. Can be anything.
    def update_record(self, identifier, type=None, name=None, content=None):
        record = [{
            'data': content,
        }]
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')

        payload = self._put(self._domain_record_path(type, name), record)
        print 'update_record: {0}'.format(payload)
        return payload['code'] if payload['code'] else True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        payload, records = self._list_records(type)
        print 'delete_record: {0}'.format(payload)
        total = len(records)

        print 'delete_record: type records to filter: {0}'.format(records)

        records = [record for record in records if record['name'] != self._full_name(name) or (record['name'] == self._full_name(name) and record['content'] != content)]

        print 'delete_record: Keeping {0} of {1}'.format(len(records), total)
        print 'delete_record: type records to keep: {0}'.format(records)

        #payload = self._put(self._domain_record_path(type), records)
        #print 'delete_record: {0}'.format(payload)
        return True if payload == "" else False

    def _list_records(self, type=None, name=None, content=None):
        payload = self._get(self._domain_record_path(type, name))

        records = []
        for record in payload:
            processed_record = {key: record[key] for key in record if key in ['type', 'name', 'ttl']}
            processed_record['content'] = record['data']
            processed_record['id'] = len(records)
            records.append(processed_record)

        if content:
            records = [record for record in records if record['content'] == content]

        return [payload, records]

    def _domain_record_path(self, type=None, name=None):
        path = '/domains/{0}/records'.format(self.options['domain'])
        if type:
            path = '{0}/{1}'.format(path, str(type).capitalize())
        if name:
            path = '{0}/{1}'.format(path, name)
        return path

    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': "sso-key " + self.options['auth_access_key'] + ":" + self.options['auth_access_secret']
        }

        if self.options.get('shopper_id'):
            default_headers['X-Shopper-Id'] = self.options.get('shopper_id')

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=None)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()