"""Main module of Lexicon. Defines the Client class, that holds all Lexicon logic."""
from __future__ import absolute_import
import importlib
import os

import tldextract

from lexicon import discovery
from lexicon.config import (
    ConfigResolver, DictConfigSource,
    legacy_config_resolver, non_interactive_config_resolver,
)

TLDEXTRACT_CACHE_FILE_DEFAULT = os.path.join('~', '.lexicon_tld_set')
TLDEXTRACT_CACHE_FILE = os.path.expanduser(os.environ.get("LEXICON_TLDEXTRACT_CACHE",
                                                          TLDEXTRACT_CACHE_FILE_DEFAULT))

class ProviderNotAvailableError(Exception):
    """
    Custom exception to raise when a provider is not available,
    typically because some optional dependencies are missing
    """


class Client(object):  # pylint: disable=useless-object-inheritance,too-few-public-methods
    """This is the Lexicon client, that will execute all the logic."""

    def __init__(self, config=None):
        if not config:
            # If there is not config specified, we load a non-interactive configuration.
            self.config = non_interactive_config_resolver()
        elif not isinstance(config, ConfigResolver):
            # If config is not a ConfigResolver, we are in a legacy situation.
            # We protect this part of the Client API.
            self.config = legacy_config_resolver(config)
        else:
            self.config = config

        # Validate configuration
        self._validate_config()

        runtime_config = {}

        # Process domain, strip subdomain
        domain_extractor = tldextract.TLDExtract(cache_file=TLDEXTRACT_CACHE_FILE,
                                                 include_psl_private_domains=True)
        domain_parts = domain_extractor(
            self.config.resolve('lexicon:domain'))
        runtime_config['domain'] = '{0}.{1}'.format(
            domain_parts.domain, domain_parts.suffix)

        if self.config.resolve('lexicon:delegated'):
            # handle delegated domain
            delegated = self.config.resolve('lexicon:delegated').rstrip('.')
            if delegated != runtime_config.get('domain'):
                # convert to relative name
                if delegated.endswith(runtime_config.get('domain')):
                    delegated = delegated[:-len(runtime_config.get('domain'))]
                    delegated = delegated.rstrip('.')
                # update domain
                runtime_config['domain'] = '{0}.{1}'.format(
                    delegated, runtime_config.get('domain'))

        self.action = self.config.resolve('lexicon:action')
        self.provider_name = (self.config.resolve('lexicon:provider_name')
                              or self.config.resolve('lexicon:provider'))

        self.config.add_config_source(DictConfigSource(runtime_config), 0)

        provider_module = importlib.import_module(
            'lexicon.providers.' + self.provider_name)
        provider_class = getattr(provider_module, 'Provider')
        self.provider = provider_class(self.config)

    def execute(self):
        """Execute provided configuration in class constructor to the DNS records"""
        self.provider.authenticate()
        identifier = self.config.resolve('lexicon:identifier')
        record_type = self.config.resolve('lexicon:type')
        name = self.config.resolve('lexicon:name')
        content = self.config.resolve('lexicon:content')

        if self.action == 'create':
            return self.provider.create_record(record_type, name, content)

        if self.action == 'list':
            return self.provider.list_records(record_type, name, content)

        if self.action == 'update':
            return self.provider.update_record(identifier, record_type, name, content)

        if self.action == 'delete':
            return self.provider.delete_record(identifier, record_type, name, content)

        raise ValueError('Invalid action statement: {0}'.format(self.action))

    def _validate_config(self):
        provider_name = self.config.resolve('lexicon:provider_name')
        if not self.config.resolve('lexicon:provider_name'):
            raise AttributeError('provider_name')

        try:
            available = discovery.find_providers()[self.config.resolve('lexicon:provider_name')]
        except KeyError:
            raise ProviderNotAvailableError('This provider ({0}) is not supported by Lexicon.'
                                            .format(provider_name))
        else:
            if not available:
                raise ProviderNotAvailableError(
                    'This provider ({0}) has required dependencies that are missing. '
                    'Please install lexicon[{0}] first.'.format(provider_name))

        if not self.config.resolve('lexicon:action'):
            raise AttributeError('action')
        if not self.config.resolve('lexicon:domain'):
            raise AttributeError('domain')
        if not self.config.resolve('lexicon:type'):
            raise AttributeError('type')
