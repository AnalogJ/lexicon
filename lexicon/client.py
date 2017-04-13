from builtins import object
import importlib
import os
import tldextract
from .common.options_handler import env_auth_options

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

        if self.action == 'create':
            return self.provider.create_record(self.options.get('type'), self.options.get('name'), self.options.get('content'))

        elif self.action == 'list':
            return self.provider.list_records(self.options.get('type'), self.options.get('name'), self.options.get('content'))

        elif self.action == 'update':
            return self.provider.update_record(self.options.get('identifier'), self.options.get('type'), self.options.get('name'), self.options.get('content'))

        elif self.action == 'delete':
            return self.provider.delete_record(self.options.get('identifier'), self.options.get('type'), self.options.get('name'), self.options.get('content'))

    def _validate(self, options):
        if not options.get('provider_name'):
            raise AttributeError('provider_name')
        if not options.get('action'):
            raise AttributeError('action')
        if not options.get('domain'):
            raise AttributeError('domain')
        if not options.get('type'):
            raise AttributeError('type')