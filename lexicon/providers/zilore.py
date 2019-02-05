import logging

import requests

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['zilore.net']


def provider_parser(subparser):
    subparser.description = '''
    Zilore API requires an API key that can be found in your Zilore profile, at the API tab.
    The API access is available only for paid plans.
    '''
    subparser.add_argument('--auth-key', help='specify the Zilore API key to use')


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None

    def authenticate(self):
        result = self._get('/domains')

        target_domain = [item for item in result['response']
                         if item['domain_name'] == self.domain]

        if not target_domain:
            raise Exception('Domain {0} is not available on this account'.format(self.domain))

        self.domain_id = target_domain[0]['domain_id']

    def _list_records(self, rtype=None, name=None, content=None):
        result = self._get('/domains/{0}/records'.format(self.domain), {})

        records = [self._clean_TXT_record({
            'id': item['record_id'],
            'type': item['record_type'],
            'name': self._full_name(item['record_name']),
            'content': item['record_value'],
            'ttl': item['record_ttl']
        }) for item in result['response']]

        if rtype:
            records = [record for record in records if record['type'] == rtype]
        if name:
            records = [record for record in records if record['name'] == self._full_name(rtype)]
        if content:
            records = [record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)

        return records

    def _create_record(self, rtype, name, content):
        if not rtype or not name or not content:
            raise Exception(
                'Error, rtype, name and content are mandatory to create a record.')

        records = self._list_records(rtype, name, content)

        if records:
            LOGGER.debug('not creating a duplicate record: %s', records[0])
            return True

        record = {
            'record_type': rtype,
            'record_name': self._full_name(name),
            'record_value': content if rtype != 'TXT' else '"{0}"'.format(content)
        }

        if self._get_lexicon_option('ttl'):
            record['record_ttl'] = self._get_lexicon_option('ttl')

        result = self._post('/domains/{0}/records'.format(self.domain), data=record)

        LOGGER.debug('create_record: %s', result['response'][0]['record_id'])

        return True

    def _request(self, action='GET', url='/', data=None, query_params=None):
        print(query_params)
        response = requests.request(action, 'https://api.zilore.com/dns/v1{0}'.format(url),
                                    params=query_params, json=data,
                                    headers={'X-Auth-Key': self._get_provider_option('auth_key')})
        response.raise_for_status()

        return response.json()
