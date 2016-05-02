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

        self._parse_env()

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

    def _parse_env(self):
        # make sure that auth parameters can be specified via environmental variables as well.
        # basically we map env variables for the chosen provider to the options dictionary (if a value isnt already provided)
        # LEXICON_CLOUDFLARE_TOKEN => options['auth_token']
        # LEXICON_CLOUDFLARE_USERNAME => options['auth_username']
        # LEXICON_CLOUDFLARE_PASSWORD => options['auth_password']
        env_prefix = 'LEXICON_{0}_'.format(self.provider_name.upper())
        for key in os.environ.keys():
            if key.startswith(env_prefix):
                auth_type = key[len(env_prefix):].lower()
                # only assign auth_username/token/etc if its not already provided by CLI.
                if self.options.get('auth_{0}'.format(auth_type)) is None:
                    self.options['auth_{0}'.format(auth_type)] = os.environ[key]

    def _validate(self, options):
        if not options.get('provider_name'):
            raise AttributeError('provider_name')
        if not options.get('action'):
            raise AttributeError('action')
        if not options.get('domain'):
            raise AttributeError('domain')
        if not options.get('type'):
            raise AttributeError('type')