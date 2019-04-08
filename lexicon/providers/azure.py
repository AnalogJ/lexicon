import binascii
import logging

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
import requests

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)
AZURE_AD_URL = 'https://login.microsoftonline.com'
MANAGEMENT_URL = 'https://management.azure.com'
API_VERSION = '2018-03-01-preview'
NAMESERVER_DOMAINS = ['azure.com']


def provider_parser(subparser):
    subparser.add_argument('--auth-client-id')
    subparser.add_argument('--auth-client-secret')
    subparser.add_argument('--auth-tenant-id')
    subparser.add_argument('--subscription-id')
    subparser.add_argument('--resource-group')


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self._access_token = None
        self._subscription_id = None

    def _list_records(self, rtype=None, name=None, content=None):
        result = self._get('/{0}'.format(rtype if rtype else 'recordsets'))

        records = []
        for raw_record in result['value']:
            rtype = raw_record['type'].replace('Microsoft.Network/dnszones/', '')
            for value in _get_values_from_recordset(rtype, raw_record):
                record = {
                    'type': rtype,
                    'name': self._full_name(raw_record['name']),
                    'ttl': raw_record['properties']['TTL'],
                    'content': value
                }
                record['id'] = _identifier(record)
                records.append(record)

        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)

        return records

    def _create_record(self, rtype, name, content):
        if not rtype or not name or not content:
            raise Exception('Error, rtype, name and content are mandatory to create a record.')

        identifier = _identifier(
            {'type': rtype, 'name': self._full_name(name), 'content': content})

        records = self._list_records(rtype, name)

        if [record for record in records if record['id'] == identifier]:
            LOGGER.debug('create_record (ignored, duplicate): %s', identifier)
            return True

        values = [record['content'] for record in records]
        values.append(content)

        properties = _build_recordset_from_values(rtype, values)

        ttl = self._get_lexicon_option('ttl')
        if ttl:
            properties['TTL'] = ttl

        self._put('/{0}/{1}'.format(rtype, self._relative_name(name)),
                  data={'properties': properties})

        LOGGER.debug('create_record: %s', identifier)

        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier and (not rtype or not name):
            raise Exception(
                'Error, identifier or rtype+name parameters are required.')

        if identifier:
            records = self._list_records()
            records_to_update = [
                record for record in records if record['id'] == identifier]
        else:
            records_to_update = self._list_records(rtype=rtype, name=name)

        if not records_to_update:
            if identifier:
                raise Exception('Error, could not find a record for given identifier: {0}'
                                .format(identifier))
            else:
                raise Exception('Error, could not find a record for given type and name: {0} {1}'
                                .format(rtype, name))

        if len(records_to_update) > 1:
            LOGGER.warning('Warning, multiple records found for given parameters, '
                           'only first one will be updated: %s', records_to_update)

    def _authenticate(self):
        tenant_id = self._get_provider_option('auth_tenant_id')
        client_id = self._get_provider_option('auth_client_id')
        client_secret = self._get_provider_option('auth_client_secret')
        self._subscription_id = self._get_provider_option('subscription_id')
        self._resource_group = self._get_provider_option('resource_group')

        assert tenant_id
        assert client_id
        assert client_secret
        assert self._subscription_id
        assert self._resource_group

        url = '{0}/{1}/oauth2/token'.format(AZURE_AD_URL, tenant_id)
        data = {
            'grant_type': 'client_credentials',
            'client_id': client_id,
            'client_secret': client_secret,
            'resource': MANAGEMENT_URL
        }

        result = requests.post(url, data=data)
        result.raise_for_status()

        self._access_token = result.json()['access_token']

        url = ('{0}/subscriptions/{1}/resourceGroups/{2}/providers/Microsoft.Network/dnsZones'
               .format(MANAGEMENT_URL, self._subscription_id, self._resource_group))
        headers = {'Authorization': 'Bearer {0}'.format(self._access_token)}
        params = {'api-version': API_VERSION}

        result = requests.get(url, headers=headers, params=params)
        result.raise_for_status()

        data = result.json()

        our_data = [one_data for one_data in data['value'] if one_data['name'] == self.domain]

        if not our_data:
            raise Exception('Resource group `{0}` in subscription `{1}` '
                            'does not contain the DNS zone `{1}`'
                            .format(self._resource_group, self._subscription_id, self.domain))

        self.domain_id = our_data[0]['id']

    def _request(self, action='GET', url='/', data=None, query_params=None):
        query_params = {} if not query_params else query_params.copy()
        query_params['api-version'] = API_VERSION
        request = requests.request(action, MANAGEMENT_URL + self.domain_id + url,
                                   params=query_params,
                                   json=None if not data else data,
                                   headers={'Authorization': 'Bearer {0}'.format(self._access_token)})
        print(request.json())
        request.raise_for_status()
        return request.json()


def _get_values_from_recordset(rtype, record):
    properties = record['properties']
    if rtype == 'A':
        return [entry['ipv4Address'] for entry in properties['ARecords']]
    if rtype == 'AAAA':
        return [entry['ipv6Address'] for entry in properties['AAAARecords']]
    if rtype == 'CNAME':
        return [entry['cname'] for entry in properties['CNAMERecords']]
    if rtype == 'MX':
        return [entry['exchange'] for entry in properties['MXRecords']]
    if rtype == 'SOA':
        return [entry['email'] for entry in properties['SOARecord']]
    if rtype == 'TXT':
        return [value for entry in properties['TXTRecords'] for value in entry['value']]
    if rtype == 'SRV':
        return [entry['target'] for entry in properties['SRVRecords']]

    raise Exception('Error, `{0}` entries are not supported by this provider.'.format(rtype))


def _build_recordset_from_values(rtype, values):
    if rtype == 'A':
        return {'ARecords': [{'ipv4Address': value} for value in values]}
    if rtype == 'AAAA':
        return {'AAAARecords': [{'ipv6Address': value} for value in values]}
    if rtype == 'CNAME':
        return {'CNAMERecords': [{'cname': value} for value in values]}
    if rtype == 'MX':
        return {'MXRecords': [{'exchange': value} for value in values]}
    if rtype == 'SOA':
        return {'SOARecords': [{'email': value} for value in values]}
    if rtype == 'TXT':
        return {'TXTRecords': [{'value': values}]}
    if rtype == 'SRV':
        return {'SRVRecords': [{'target': value} for value in values]}

    raise Exception('Error, `{0}` entries are not supported by this provider.'.format(rtype))


def _identifier(record):
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(('type=' + record.get('type', '') + ',').encode('utf-8'))
    digest.update(('name=' + record.get('name', '') + ',').encode('utf-8'))
    digest.update(('content=' + record.get('content', '') + ',').encode('utf-8'))

    return binascii.hexlify(digest.finalize()).decode('utf-8')[0:7]
