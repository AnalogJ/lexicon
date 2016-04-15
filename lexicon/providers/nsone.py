from base import Provider as BaseProvider
import requests
import json

def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify token used authenticate to DNS provider")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = provider_options.get('api_endpoint') or 'https://api.nsone.net/v1'

    def authenticate(self):

        payload = self._get('/zones/{0}'.format(self.options['domain']))

        if not payload['id']:
            raise StandardError('No domain found')

        self.domain_id = self.options['domain']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'type': type,
            'domain': self._full_name(name),
            'zone': self.domain_id,
            'answers':[
                {"answer": [content]}
            ]
        }
        payload = {}
        try:
            payload = self._put('/zones/{0}/{1}/{2}'.format(self.domain_id, self._full_name(name),type), record)
        except requests.exceptions.HTTPError, e:
            if e.response.status_code == 400:
                payload = {}

                # http 400 is ok here, because the record probably already exists
        print 'create_record: {0}'.format('id' in payload)
        return 'id' in payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filter = {}

        payload = self._get('/zones/{0}'.format(self.domain_id))
        records = []
        for record in payload['records']:
            processed_record = {
                'type': record['type'],
                'name': record['domain'],
                'ttl': record['ttl'],
                'content': record['short_answers'][0],
                #this id is useless unless your doing record linking. Lets return the original record identifier.
                'id': '{0}/{1}/{2}'.format(self.domain_id, record['domain'], record['type']) #
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

        data = {}
        payload = None
        new_identifier = "{0}/{1}/{2}".format(self.domain_id, self._full_name(name),type)

        if(new_identifier == identifier or (type is None and name is None)):
            # the identifier hasnt changed, or type and name are both unspecified, only update the content.
            data['answers'] = [
                {"answer": [content]}
            ]
            self._post('/zones/{0}'.format(identifier), data)

        else:
            # identifiers are different
            # get the old record, create a new one with updated data, delete the old record.
            old_record = self._get('/zones/{0}'.format(identifier))
            self.create_record(type or old_record['type'], name or old_record['domain'], content or old_record['answers'][0]['answer'][0])
            self.delete_record(identifier)

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
        payload = self._delete('/zones/{0}'.format(identifier))

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
            'Content-Type': 'application/json',
            'X-NSONE-Key': self.options['auth_token']
        }
        default_auth = None

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
