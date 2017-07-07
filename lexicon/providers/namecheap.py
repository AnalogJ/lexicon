from __future__ import absolute_import
from __future__ import print_function

import logging

import namecheap

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument(
        '--auth-token',
        help='specify api token used to authenticate',
        required=True
    )
    subparser.add_argument(
        '--auth-username',
        help='specify email address used to authenticate',
        required=True
    )
    # FIXME What is the client IP used for?
    subparser.add_argument(
        '--auth-client-ip',
        help='Client IP address to send to Namecheap API calls',
        default='127.0.0.1'
    )
    subparser.add_argument(
        '--auth-sandbox',
        help='Whether to use the sandbox server',
        action='store_true'
    )

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.options = options
        self.client = namecheap.Api(
            ApiUser=options['auth_username'],
            ApiKey=options['auth_token'],
            UserName=options['auth_username'],
            ClientIP=options['auth_client_ip'],
            sandbox=options.get('auth_sandbox', False),
            debug=False
        )
        self.domain = self.options['domain']
        self.domain_id = None

    def authenticate(self):
        try:
            domain_names = [x['Name'] for x in self.client.domains_getList()]
        except namecheap.ApiError:
            raise Exception('Authentication failed')
        if self.domain not in domain_names:
            raise Exception('The domain {} is not controlled by this Namecheap '
                            'account'.format(self.domain))
        # FIXME What is this for?
        self.domain_id = self.domain

    # Create record. If record already exists with the same content, do nothing
    def create_record(self, type, name, content):
        record = {
            # required
            'Type': type,
            'Name': self._relative_name(name),
            'Address': content
        }
        # logger.debug('create_record: %s', 'id' in payload)
        # return 'id' in payload
        return self.client.domains_dns_addHost(self.domain, record)

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is
    # received.
    def list_records(self, type=None, name=None, content=None):
        records = []
        raw_records = self.client.domains_dns_getHosts(self.domain)
        for record in raw_records:
            processed_record = {
                'type': record['Type'],
                'name': '{0}.{1}'.format(record['Name'], self.domain),
                'ttl': record['TTL'],
                'content': record['Address'],
                'id': record['HostId']
            }
            records.append(processed_record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == '{0}.{1}'.format(name, self.domain)]
        if content:
            records = [record for record in records if record['content'].lower() == content.lower()]

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        # Delete record if it exists
        self.delete_record(identifier, type, name, content)
        return self.create_record(type, name, content)

    def _find_record(self, name, type=None):
        '''
        Find a Namecheap Record based on its name and type (optional)
        '''
        raw_records = self.client.domains_dns_getHosts(self.domain)
        for record in raw_records:
            if record['Name'] == name:
                if type:
                    if record['Type'] == type:
                        return record
                else:
                    return record

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        # FIXME identifier parameter is ignored
        record = self._find_record(name=name, type=type)
        if record:
            return self.client.domains_dns_delHost(self.domain, record)
