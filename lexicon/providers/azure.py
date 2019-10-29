"""
Implement the Azure DNS provider.
The Azure DNS API is well documented, with meaningful examples.
The major difficulties are the authentication, that uses OAuth, and require several authentication
parameters, and the fact that records are manipulated as recordsets (entries with multiple values
like TXT are hold on a unique TXTRecords object), and so require methods to go from the Azure
representation of a DNS record to the Lexicon one. To simplify the implementation then, update
actions are managed using the create and delete actions: updating a record consists in removing the
old record, then creating a new record with updated parameters. Note also that Azure DNS does not
support id on records (as they are hold in a recordset) so an id is generated on the fly.
"""
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
NAMESERVER_DOMAINS = ['azure-dns.com', 'azure-dns.net', 'azure-dns.org', 'azure-dns.info']

SUPPORTED_RECORDS = {'A', 'AAAA', 'CNAME', 'MX', 'NS', 'SOA', 'TXT', 'SRV'}


def provider_parser(subparser):
    """Generate a subparser for Azure DNS"""
    subparser.description = '''
        The Azure provider orchestrates the DNS zones hosted in a resource group for a subscription
        in Microsoft Azure Cloud. To authenticate, an App registration must be created in an Azure
        Active Directory. This App registration must be granted Admin for API permissions to
        Domain.ReadWrite.All" to this Active Directory, and must have a usable Client secret.
    '''
    subparser.add_argument('--auth-client-id', help='specify the client ID (aka application ID) '
                                                    'of the App registration')
    subparser.add_argument('--auth-client-secret', help='specify the client secret of the App '
                                                        'registration')
    subparser.add_argument('--auth-tenant-id', help='specify the tenant ID (aka directory ID) of '
                                                    'the App registration')
    subparser.add_argument('--auth-subscription-id', help='specify the subscription ID attached '
                                                          'to the resource group')
    subparser.add_argument('--resource-group', help='specify the resource group hosting the DNS '
                                                    'zone to edit')


class Provider(BaseProvider):
    """Provider for Azure DNS"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self._access_token = None

    def _list_records(self, rtype=None, name=None, content=None):
        result = self._get('/{0}'.format(rtype if rtype else 'recordsets'))

        records = []
        for raw_record in result['value']:
            rtype = raw_record['type'].replace('Microsoft.Network/dnszones/', '')
            if rtype not in SUPPORTED_RECORDS:
                continue
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
        identifier = self._create_record_internal(rtype, name, content)

        LOGGER.debug('create_record: %s', identifier)

        return True

    def _create_record_internal(self, rtype, name, content):
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

        return identifier

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
            raise Exception(
                'Error, could not find a record for given identifier: {0}'.format(identifier))

        if len(records_to_update) > 1:
            LOGGER.warning(
                'Warning, multiple records found for given parameters, '
                'only first one will be updated: %s', records_to_update)

        identifier = identifier if identifier else records_to_update[0]['id']
        rtype = rtype if rtype else records_to_update[0]['type']
        name = name if name else records_to_update[0]['name']
        content = content if content else records_to_update[0]['content']

        self._delete_record_internal(identifier=identifier)
        self._create_record_internal(rtype=rtype, name=name, content=content)

        LOGGER.debug('update_record: %s => %s', identifier,
                     _identifier({'type': rtype, 'name': name, 'content': content}))

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        self._delete_record_internal(identifier, rtype, name, content)

        LOGGER.debug('delete_records: %s %s %s %s',
                     identifier, rtype, name, content)

        return True

    def _delete_record_internal(self, identifier=None, rtype=None, name=None, content=None):  # pylint: disable=too-many-locals
        result = self._get('/{0}'.format(rtype if rtype else 'recordsets'))

        to_delete = []
        to_shrink = []
        for record in result['value']:
            record_rtype = record['type'].replace('Microsoft.Network/dnszones/', '')
            if record_rtype not in SUPPORTED_RECORDS:
                continue
            new_values = []
            values = _get_values_from_recordset(record_rtype, record)
            for value in values:
                if identifier is not None and identifier != _identifier(
                        {'type': record_rtype,
                         'name': self._full_name(record['name']),
                         'content': value}):
                    new_values.append(value)
                elif identifier is None:
                    matching_rtype = rtype is None or record_rtype == rtype
                    matching_name = (name is None or
                                     self._full_name(name) == self._full_name(record['name']))
                    matching_content = content is None or value == content
                    if not (matching_rtype and matching_name and matching_content):
                        new_values.append(value)

            to_modify = len(values) != len(new_values)
            if to_modify:
                record['properties'].update(_build_recordset_from_values(record_rtype, new_values))
                if new_values:
                    to_shrink.append(record)
                else:
                    to_delete.append(record)

        for record in to_delete:
            record_rtype = record['type'].replace('Microsoft.Network/dnszones/', '')
            self._delete('/{0}/{1}'.format(record_rtype, self._relative_name(record['name'])))
        for record in to_shrink:
            record_rtype = record['type'].replace('Microsoft.Network/dnszones/', '')
            self._request('PATCH', '/{0}/{1}'
                          .format(record_rtype, self._relative_name(record['name'])),
                          data={'properties': record['properties']})

    def _authenticate(self):
        tenant_id = self._get_provider_option('auth_tenant_id')
        client_id = self._get_provider_option('auth_client_id')
        client_secret = self._get_provider_option('auth_client_secret')
        subscription_id = self._get_provider_option('auth_subscription_id')
        resource_group = self._get_provider_option('resource_group')

        assert tenant_id
        assert client_id
        assert client_secret
        assert subscription_id
        assert resource_group

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
               .format(MANAGEMENT_URL, subscription_id, resource_group))
        headers = {'Authorization': 'Bearer {0}'.format(self._access_token)}
        params = {'api-version': API_VERSION}

        result = requests.get(url, headers=headers, params=params)
        result.raise_for_status()

        data = result.json()

        our_data = [one_data for one_data in data['value'] if one_data['name'] == self.domain]

        if not our_data:
            raise Exception('Resource group `{0}` in subscription `{1}` '
                            'does not contain the DNS zone `{2}`'
                            .format(resource_group, subscription_id, self.domain))

        self.domain_id = our_data[0]['id']

    def _request(self, action='GET', url='/', data=None, query_params=None):
        query_params = {} if not query_params else query_params.copy()
        query_params['api-version'] = API_VERSION
        headers = {'Authorization': 'Bearer {0}'.format(self._access_token)}
        request = requests.request(action, MANAGEMENT_URL + self.domain_id + url,
                                   params=query_params, headers=headers,
                                   json=None if not data else data)
        request.raise_for_status()
        if request.content:
            return request.json()
        return None


def _get_values_from_recordset(rtype, record):
    properties = record['properties']
    values = None
    if rtype == 'A':
        values = [entry['ipv4Address'] for entry in properties['ARecords']]
    if rtype == 'AAAA':
        values = [entry['ipv6Address'] for entry in properties['AAAARecords']]
    if rtype == 'CNAME':
        values = [properties['CNAMERecord']['cname']]
    if rtype == 'MX':
        values = [entry['exchange'] for entry in properties['MXRecords']]
    if rtype == 'NS':
        values = [entry['nsdname'] for entry in properties['NSRecords']]
    if rtype == 'SOA':
        values = [properties['SOARecord']['email']]
    if rtype == 'TXT':
        values = [value for entry in properties['TXTRecords'] for value in entry['value']]
    if rtype == 'SRV':
        values = [entry['target'] for entry in properties['SRVRecords']]

    if values:
        return values

    raise Exception('Error, `{0}` entries are not supported by this provider.'.format(rtype))


def _build_recordset_from_values(rtype, values):
    recordset = None
    if rtype == 'A':
        recordset = {'ARecords': [{'ipv4Address': value} for value in values]}
    if rtype == 'AAAA':
        recordset = {'AAAARecords': [{'ipv6Address': value} for value in values]}
    if rtype == 'CNAME':
        recordset = {'CNAMERecord': {'cname': values[0]} if values else {}}
    if rtype == 'MX':
        recordset = {'MXRecords': [{'exchange': value} for value in values]}
    if rtype == 'NS':
        recordset = {'NSRecords': [{'nsdname': value} for value in values]}
    if rtype == 'SOA':
        recordset = {'SOARecord': {'email': values[0]} if values else {}}
    if rtype == 'TXT':
        recordset = {'TXTRecords': [{'value': values}]}
    if rtype == 'SRV':
        recordset = {'SRVRecords': [{'target': value} for value in values]}

    if recordset:
        return recordset

    raise Exception('Error, `{0}` entries are not supported by this provider.'.format(rtype))


def _identifier(record):
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(('type=' + record.get('type', '') + ',').encode('utf-8'))
    digest.update(('name=' + record.get('name', '') + ',').encode('utf-8'))
    digest.update(('content=' + record.get('content', '') + ',').encode('utf-8'))

    return binascii.hexlify(digest.finalize()).decode('utf-8')[0:7]
