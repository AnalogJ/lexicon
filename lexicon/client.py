from builtins import object
import importlib
import logging
import os
import tldextract
import lexicon.common.records as DnsRecords
from .common.options_handler import env_auth_options

logger = logging.getLogger(__name__)

#from providers import Example
class Client(object):
    def __init__(self, cli_options):
        #validate options
        self._validate(cli_options)

        #process domain, strip subdomain
        domain_parts = tldextract.extract(cli_options.get('domain'))
        cli_options['domain'] = '{0}.{1}'.format(domain_parts.domain, domain_parts.suffix)

        if cli_options.get('delegated'):
            # handle delegated domain
            delegated = cli_options.get('delegated').rstrip('.')
            if delegated != cli_options.get('domain'):
                # convert to relative name
                if delegated.endswith(cli_options.get('domain')):
                    delegated = delegated[:-len(cli_options.get('domain'))]
                    delegated = delegated.rstrip('.')
                # update domain
                cli_options['domain'] = '{0}.{1}'.format(delegated, cli_options.get('domain'))

        self.action = cli_options.get('action')
        self.provider_name = cli_options.get('provider_name')
        self.options = env_auth_options(self.provider_name)
        self.options.update(cli_options)

        provider_module = importlib.import_module('lexicon.providers.' + self.provider_name)
        provider_class = getattr(provider_module, 'Provider')
        self.provider = provider_class(self.options)

    def execute(self):
        self.provider.authenticate()

        record_type = self.options.get('type')
        record_type = record_type.upper().strip()
        record = DnsRecords.RecordFactory.create_record(record_type,
            name=self.options.get('name'),
            content=self.options.get('content'),
            ttl=self.options.get('ttl', None),
            priority=self.options.get('mx-priority', 0))
        if not record:
            logger.error("Unknown record type: {0}".format(self.options.get('type')))
            return

        filter_record = None
        if self.action == 'update':
            filter_record = DnsRecords.RecordFactory.create_record(record.type,
                id=self.options.get('identifier', None),
                name=record.name,
                content=self.options.get('content-old', None))
        elif self.action == 'delete':
            filter_record = record
            filter_record.id = self.options.get('identifier', None)

        if self.action == 'create':
            return self.provider.create_record(record)
        elif self.action == 'list':
            filter_record = record
            return self.provider.list_records(filter_record)
        elif self.action == 'update':
            return self.provider.update_record(filter_record, record)
        elif self.action == 'delete':
            return self.provider.delete_record(filter_record)

    def _validate(self, options):
        if not options.get('provider_name'):
            raise AttributeError('provider_name')
        if not options.get('action'):
            raise AttributeError('action')
        if not options.get('domain'):
            raise AttributeError('domain')
        if not options.get('type'):
            raise AttributeError('type')

