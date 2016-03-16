import importlib
import os
import tldextract
#from providers import Example
class Client:
    def __init__(self, options):
        #validate options
        self._validate(options)

        #process domain, strip subdomain
        domain_parts = tldextract.extract(options.get('domain'))
        options['domain'] = '{0}.{1}'.format(domain_parts.domain, domain_parts.suffix)

        self.action = options.get('action')
        self.provider_name = options.get('provider_name')
        self.options = options

        # make sure that auth parameters can be specified via environmental variables as well.
        self.options['auth_username'] = self.options.get('auth_username') or os.environ.get('LEXICON_{0}_USERNAME'.format(self.provider_name.upper()))
        self.options['auth_password'] = self.options.get('auth_password') or os.environ.get('LEXICON_{0}_PASSWORD'.format(self.provider_name.upper()))
        self.options['auth_token'] = self.options.get('auth_token') or os.environ.get('LEXICON_{0}_TOKEN'.format(self.provider_name.upper()))

        provider_module = importlib.import_module('lexicon.providers.' + self.provider_name)
        # TODO: this should not be enabled in production
        #provider_module = importlib.import_module('providers.' + self.provider_name)

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