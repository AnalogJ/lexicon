from __future__ import absolute_import
from __future__ import print_function

import logging

from .base import Provider as BaseProvider

try:
    import SoftLayer
except ImportError:
    pass

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify username used to authenticate")
    subparser.add_argument("--auth-api-key", help="specify API private key to authenticate")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None

        username = self.options.get('auth_username')
        api_key = self.options.get('auth_api_key')

        if not username or not api_key:
            raise Exception("No username and/or api key was specified")

        sl_client = SoftLayer.create_client_from_env(username=username, api_key=api_key)
        self.sl_dns = SoftLayer.managers.dns.DNSManager(sl_client)


    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider, so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason, of if the domain does not exist.
    def authenticate(self):
        domain = self.options.get('domain')

        payload = self.sl_dns.resolve_ids(domain)

        if len(payload) < 1:
            raise Exception('No domain found')
        if len(payload) > 1:
            raise Exception('Too many domains found. This should not happen')

        logger.debug('domain id: %s', payload[0])
        self.domain_id = payload[0]


    # Create record. If record already exists with the same content, do nothing
    def create_record(self, type, name, content):
        records = self.list_records(type,name,content)
        if len(records) > 0:
            # Nothing to do, record already exists
            logger.debug('create_record: already exists')
            return True

        name = self._relative_name(name)
        ttl = self.options.get('ttl')
        payload = self.sl_dns.create_record(self.domain_id,name,type,content,ttl)

        logger.debug('create_record: %s', payload)
        return True


    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        ttl=None
        if name:
            name = self._relative_name(name)

        payload = self.sl_dns.get_records(self.domain_id,ttl,content,name,type)

        records = []
        for record in payload:
            processed_record = {
                'type': record['type'].upper(),
                'name': self._full_name(record['host']),
                'ttl': record['ttl'],
                'content': record['data'],
                'id': record['id']
            }
            records.append(processed_record)

        logger.debug('list_records: %s', records)
        return records


    # Update a record.
    # If an identifier is specified, use it, otherwise do a lookup using type and name.
    def update_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')

        record = { 'id': identifier }
        if type:
            record['type'] = type
        if name:
            record['host'] = self._relative_name(name)
        if content:
            record['data'] = content
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')

        payload = self.sl_dns.edit_record(record)

        logger.debug('update_record: %s', payload)
        return True


    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self.list_records(type, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)
        
        logger.debug('delete_records: %s', delete_record_id)
        
        for record_id in delete_record_id:
            payload = self.sl_dns.delete_record(record_id)

        logger.debug('delete_record: %s', True)
        return True

