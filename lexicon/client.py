import importlib
import os
import tldextract
#from providers import Example
class Client:
    def __init__(self, options):
        #process domain, strip subdomain
        domain_parts = tldextract.extract(options.domain)
        options.domain = '{0}.{1}'.format(domain_parts.domain, domain_parts.suffix)
        options.subdomain = domain_parts.subdomain

        self.action = options.action
        self.provider_name = options.provider_name
        self.options = options

        # validate options


        # make sure that auth parameters can be specified via environmental variables as well.
        self.options.auth_username = self.options.auth_username or os.environ.get('LEXICON_{0}_USERNAME'.format(self.provider_name.upper()))
        self.options.auth_password = self.options.auth_password or os.environ.get('LEXICON_{0}_PASSWORD'.format(self.provider_name.upper()))
        self.options.auth_token = self.options.auth_token or os.environ.get('LEXICON_{0}_TOKEN'.format(self.provider_name.upper()))

        provider_module = importlib.import_module('lexicon.providers.' + self.provider_name)
        # TODO: this should not be enabled in production
        #provider_module = importlib.import_module('providers.' + self.provider_name)

        provider_class = getattr(provider_module, 'Provider')
        self.provider = provider_class(self.options)

    def execute(self):
        self.provider.authenticate()

        if self.action == 'create':
            return self.provider.create_record(self.options.type, self.options.name, self.options.content)

        elif self.action == 'list':
            return self.provider.list_records(self.options.type, self.options.name, self.options.content)

        elif self.action == 'update':
            return self.provider.update_record(self.options.identifier, self.options.type, self.options.name, self.options.content)

        elif self.action == 'delete':
            return self.provider.delete_record(self.options.identifier, self.options.type, self.options.name, self.options.content)
