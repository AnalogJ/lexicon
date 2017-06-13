from ovh import Client as OvhClient
from .base import Provider as BaseProvider

def ProviderParser(subparser):
    subparser.description = '''
        OVH Provider requires a token with full rights on /domain/*.
        It can be generated for your OVH account on the following URL: 
        https://api.ovh.com/createToken/index.cgi?GET=/domain/*&PUT=/domain/*&POST=/domain/*&DELETE=/domain/*'''
    subparser.add_argument('--auth-entrypoint', help='specify the OVH entrypoint', choices=['ovh-eu', 'ovh-ca', 'soyoustart-eu', 'soyoustart-ca', 'kimsufi-eu', 'kimsufi-ca'])
    subparser.add_argument('--auth-application-key', help='specify the application key')
    subparser.add_argument('--auth-application-secret', help='specify the application secret')
    subparser.add_argument('--auth-consumer-key', help='specify the consumer key')

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        print(self.options)
        self.ovh_client = OvhClient(
            endpoint=self.options.get('auth_entrypoint'),
            application_key=self.options.get('auth_application_key'),
            application_secret=self.options.get('auth_application_secret'),
            consumer_key=self.options.get('auth_consumer_key')
        )

    def authenticate(self):
        domain = self.options.get('domain')

        domains = self.ovh_client.get('/domain/zone')
        if domain not in domains:
            raise Exception('Domain {0} not found'.format(domain))

        status = self.ovh_client.get('/domain/zone/{0}/status'.format(domain))
        if not status['isDeployed']:
            raise Exception('Zone {0} is not deployed'.format(domain))

        self.domain_id = domain

    def create_record(self, type, name, content):
        domain = self.options.get('domain')
        ttl = self.options.get('ttl')

        config = {
            'fieldType': type,
            'subDomain': self._relative_name(name),
            'target': content
        }

        if ttl:
            config['ttl'] = ttl

        self.ovh_client.post('/domain/zone/{0}/record'.format(domain), **config)
        self.ovh_client.post('/domain/zone/{0}/refresh'.format(domain))

        return True

    def list_records(self, type=None, name=None, content=None):
        domain = self.options.get('domain')
        records = []

        config = {}
        if type:
            config['fieldType'] = type
        if name:
            config['subDomain'] = self._relative_name(name)

        record_ids = self.ovh_client.get('/domain/zone/{0}/record'.format(domain), **config)

        for record_id in record_ids:
            raw = self.ovh_client.get('/domain/zone/{0}/record/{1}'.format(domain, record_id))
            records.append({
                'type': raw['fieldType'],
                'name': '{0}.{1}'.format(raw['subDomain'], domain),
                'ttl': raw['ttl'],
                'content': raw['target'],
                'id': raw['id']
            })

        if content:
            records = [record for record in records if record['content'].lower() == content.lower()]

        return records

    def update_record(self, identifier, type=None, name=None, content=None):
        domain = self.options.get('domain')

        if not identifier:
            records = self.list_records(type, name)
            if len(records) == 1:
                identifier = records[0]['id']
            elif len(records) > 1:
                raise Exception('Several record identifiers match the request')
            else:
                raise Exception('Record identifier could not be found')

        config = {}
        if name:
            config['subDomain'] = self._relative_name(name)
        if content:
            config['target'] = content

        self.ovh_client.put('/domain/zone/{0}/record/{1}'.format(domain, identifier), **config)
        self.ovh_client.post('/domain/zone/{0}/refresh'.format(domain))

        return True

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        domain = self.options.get('domain')

        if not identifier:
            records = self.list_records(type, name, content)
            if len(records) == 1:
                identifier = records[0]['id']
            elif len(records) > 1:
                raise Exception('Several record identifiers match the request')
            else:
                raise Exception('Record identifier could not be found')

        self.ovh_client.delete('/domain/zone/{0}/record/{1}'.format(domain, identifier))
        self.ovh_client.post('/domain/zone/{0}/refresh'.format(domain))

        return True

    def _request(self, action='GET', url='/', data=None, query_params=None):
        pass # No use of this helper, we have already the OVH Client wrapper
