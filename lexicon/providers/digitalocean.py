from base import Provider as BaseProvider
import requests
import json


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-token", help="specify token used authenticate to DNS provider")


class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get(
            'api_endpoint') or 'https://api.digitalocean.com/v2'

    def authenticate(self):

        self._get('/domains/{0}'.format(self.options['domain']))
        self.domain_id = self.options['domain']

    def create_record(self, type, name, content):
        record = {
            'type': type,
            'name': self._relative_name(name),
            'data': content,

        }
        if type == 'CNAME':
            # make sure a the data is always a FQDN for CNAMe.
            record['data'] = record['data'].rstrip('.') + '.'

        self._post(
            '/domains/{0}/records'.format(self.domain_id), record)

        print 'create_record: {0}'.format(True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is
    # received.
    def list_records(self, type=None, name=None, content=None):

        url = '/domains/{0}/records'.format(self.domain_id)
        records = []
        payload = {}

        next = url
        while next is not None:
            payload = self._get(next)
            if 'links' in payload \
                    and 'pages' in payload['links'] \
                    and 'next' in payload['links']['pages']:
                next = payload['links']['pages']['next']
            else:
                next = None

            for record in payload['domain_records']:
                processed_record = {
                    'type': record['type'],
                    'name': "{0}.{1}".format(record['name'], self.domain_id),
                    'ttl': '',
                    'content': record['data'],
                    'id': record['id']
                }
                records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record[
                'name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record[
                'content'].lower() == content.lower()]

        print 'list_records: {0}'.format(records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {}
        if type:
            data['type'] = type
        if name:
            data['name'] = self._relative_name(name)
        if content:
            data['data'] = content

        self._put(
            '/domains/{0}/records/{1}'.format(self.domain_id, identifier), data)

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
        self._delete(
            '/domains/{0}/records/{1}'.format(self.domain_id, identifier))

        # is always True at this point, if a non 200 response is returned an
        # error is raised.
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
            'Content-Type': 'application/json',
            'Authorization': 'Bearer {0}'.format(self.options.get('auth_token'))
        }
        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        r = requests.request(action, url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        if action == 'DELETE':
            return ''
        else:
            return r.json()
