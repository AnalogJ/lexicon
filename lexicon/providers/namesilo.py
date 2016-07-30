from __future__ import print_function
from __future__ import absolute_import
from .base import Provider as BaseProvider
import requests
from xml.etree import ElementTree

def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify key used authenticate")


class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://www.namesilo.com/api'

    def authenticate(self):

        payload = self._get('/getDomainInfo', {'domain': self.options['domain']})
        self.domain_id = self.options['domain']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'domain': self.domain_id,
            'rrhost': self._relative_name(name),
            'rrtype': type,
            'rrvalue': content
        }
        payload = self._get('/dnsAddRecord', record)
        print('create_record: {0}'.format(True))
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        query = {'domain': self.domain_id}

        payload = self._get('/dnsListRecords', query)
        records = []
        for record in payload.find('reply').findall('resource_record'):
            processed_record = {
                'type': record.find('type').text,
                'name': record.find('host').text,
                'ttl': record.find('ttl').text,
                'content': record.find('value').text,
                'id': record.find('record_id').text
            }
            records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'] == content]

        print('list_records: {0}'.format(records))
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {
            'domain': self.domain_id,
            'rrid': identifier
        }
        # if type:
        #     data['rtype'] = type
        if name:
            data['rrhost'] = self._relative_name(name)
        if content:
            data['rdata'] = content

        payload = self._get('/dnsUpdateRecord', data)

        print('update_record: {0}'.format(True))
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        data = {
            'domain': self.domain_id
        }
        if not identifier:
            records = self.list_records(type, name, content)
            print(records)
            if len(records) == 1:
                data['rrid'] = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')
        else:
            data['rrid'] = identifier
        payload = self._get('/dnsDeleteRecord', data)

        print('delete_record: {0}'.format(True))
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        query_params['version'] = 1
        query_params['type'] = 'xml'
        query_params['key'] = self.options['auth_token']
        r = requests.request(action, self.api_endpoint + url, params=query_params)
                             #data=json.dumps(data))
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        # TODO: check if the response is an error using
        tree = ElementTree.ElementTree(ElementTree.fromstring(r.content))
        root = tree.getroot()
        if root.find('reply').find('code').text != '300':
            raise Exception('An error occurred: {0}, {1}'.format(root.find('reply').find('detail').text, root.find('reply').find('code').text))


        return root