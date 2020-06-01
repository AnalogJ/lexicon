"""Module provider for auto"""
from __future__ import absolute_import
import argparse
import importlib
import logging
import pkgutil
import re
import subprocess

import six
import tldextract
from lexicon import providers
from lexicon.config import (
    ArgsConfigSource,
    ConfigResolver,
    legacy_config_resolver,
)


LOGGER = logging.getLogger(__name__)


def _get_available_providers():
    available_providers = {}
    for _, modname, _ in pkgutil.iter_modules(providers.__path__):
        if modname not in ('base', 'auto'):
            try:
                available_providers[modname] = importlib.import_module(
                    'lexicon.providers.' + modname)
            except ImportError:
                LOGGER.warning('Warning, the provider %s cannot be loaded due '
                               'to missing optional dependencies.', modname)

    return available_providers


AVAILABLE_PROVIDERS = _get_available_providers()


def _get_ns_records_domains_for_domain(domain):
    tlds = [tldextract.extract(ns_entry)
            for ns_entry in _get_ns_records_for_domain(domain)]

    return {'{0}.{1}'.format(tld.domain, tld.suffix) for tld in tlds}


def _get_ns_records_for_domain(domain):
    # Available both for Windows and Linux (if dnsutils is installed for the latter)
    try:
        output = subprocess.check_output(['nslookup', '-querytype=NS', domain + "."],
                                         stderr=subprocess.STDOUT, universal_newlines=True)
    except subprocess.CalledProcessError as error:
        if 'NXDOMAIN' in error.output:
            raise ValueError(
                'Error, domain {0} could not be resolved.'.format(domain))
        output = error.output

    pattern = re.compile(r'nameserver = (.*?)\.*\n')
    match = pattern.findall(output)

    if not match:
        raise ValueError('Error, could not find ns entries for domain {0}. '
                         'Does this domain is correctly configured ?'.format(domain))

    return match


def _relevant_provider_for_domain(domain):
    nameserver_domains = _get_ns_records_domains_for_domain(domain)
    relevant_providers = []

    for provider_name, provider_module in AVAILABLE_PROVIDERS.items():
        ns_domains = provider_module.NAMESERVER_DOMAINS

        # Test plain domain string comparison
        if {ns_domain for ns_domain in ns_domains
                if isinstance(ns_domain, six.string_types)} & nameserver_domains:
            relevant_providers.append((provider_name, provider_module))
            continue

        # Test domains regexp matching
        for ns_domain in ns_domains:
            if hasattr(ns_domain, 'match') \
                    and [nameserver_domain for nameserver_domain
                         in nameserver_domains if ns_domain.match(nameserver_domain)]:
                relevant_providers.append((provider_name, provider_module))
                continue

    if not relevant_providers:
        raise ValueError('Error, could not find the DNS provider for given domain {0}. '
                         'Found nameservers domains are {1}'.format(domain, nameserver_domains))

    if len(relevant_providers) > 1:
        LOGGER.warning('Warning, multiple DNS providers have been found for given domain %s, '
                       'first one will be used: %s\n'
                       'This may indicate a misconfiguration in one or more provider.',
                       domain, relevant_providers)

    return relevant_providers[0]


def provider_parser(subparser):
    """Configure provider parser for auto provider"""
    subparser.description = '''
        Provider 'auto' enables the Lexicon provider auto-discovery.
        Based on the nameservers declared for the given domain,
        Lexicon will try to find the DNS provider holding the DNS zone if it is supported.
        Actual DNS zone read/write operations will be delegated to the provider found:
        every environment variable or command line specific to this provider
        can be passed to Lexicon and will be processed accordingly.
        '''
    subparser.add_argument("--mapping-override", metavar="[DOMAIN]:[PROVIDER], ...",
                           help="comma separated list of elements in the form of "
                                "[DOMAIN]:[PROVIDER] to authoritatively map a "
                                "particular domain to a particular provider")

    # Explore and load the arguments available for every provider into the 'auto' provider.
    for provider_name, provider_module in AVAILABLE_PROVIDERS.items():
        parser = argparse.ArgumentParser(add_help=False)
        provider_module.provider_parser(parser)

        for action in parser._actions:  # pylint: disable=protected-access
            action.option_strings = [re.sub(
                r'^--(.*)$', r'--{0}-\1'.format(provider_name), option)
                                     for option in action.option_strings]
            action.dest = 'auto_{0}_{1}'.format(provider_name, action.dest)
            subparser._add_action(action)  # pylint: disable=protected-access

# Take care of the fact that this provider extends object, not BaseProvider !
# Indeed we want to delegate every parameter/method call to the delegate provider
# but __getattr__ is called only if the parameter/method cannot be found in the
# current Provider hierarchy. If it is object, it will be the case for every relevant
# call in the Lexicon library.
class Provider(object):  # pylint: disable=useless-object-inheritance
    """
    Implementation of the provider 'auto'.
    For the given domain, it will resolve the actual Provider class to use by inspecting the
    nameservers declared for the domain, using declared nameservers domain in each Lexicon DNS
    provider.
    Any call upon instantiation will be delegated to the resolved Provider.
    Any command line parameter or environment variable passed to Lexicon will be transfered to
    the resolved provider if it respect the naming convention: --[provider]-[parameter_name] for a
    command line parameter, or LEXICON_[PROVIDER]_PARAMETER_NAME for a environment variable.
    """
    def __init__(self, config):
        if not isinstance(config, ConfigResolver):
            # If config is a plain dict, we are in a legacy situation.
            # To protect the Provider API, the legacy dict is handled in a
            # correctly defined ConfigResolver.
            self.config = legacy_config_resolver(config)
        else:
            self.config = config

        self.domain = config.resolve('lexicon:domain')
        self.proxy_provider = None

    def authenticate(self):  # pylint: disable=too-many-locals
        """
        Launch the authentication process: for 'auto' provider, it means first to find the relevant
        provider, then call its authenticate() method. Almost every subsequent operation will then
        be delegated to that provider.
        """
        mapping_override = self.config.resolve('lexicon:auto:mapping_override')
        mapping_override_processed = {}
        if mapping_override:
            for one_mapping in mapping_override.split(','):
                one_mapping_processed = one_mapping.split(':')
                mapping_override_processed[one_mapping_processed[0]
                                           ] = one_mapping_processed[1]

        override_provider = mapping_override_processed.get(self.domain)
        if override_provider:
            provider = [
                element for element in AVAILABLE_PROVIDERS.items()
                if element[0] == override_provider][0]
            LOGGER.info('Provider authoritatively mapped for domain %s: %s.',
                        self.domain, provider.__name__)
            (provider_name, provider_module) = provider
        else:
            (provider_name, provider_module) = _relevant_provider_for_domain(self.domain)
            LOGGER.info('Provider discovered for domain %s: %s.',
                        self.domain, provider_name)

        new_config = ConfigResolver()
        new_config.with_dict({'provider_name': provider_name})

        target_prefix = 'auto_{0}_'.format(provider_name)
        for config_source in self.config._config_sources:  # pylint: disable=protected-access
            if not isinstance(config_source, ArgsConfigSource):
                new_config.with_config_source(config_source)
            else:
                # ArgsConfigSource needs to be reprocessed to rescope the provided
                # args to the delegate provider
                new_dict = {}
                for key, value in config_source._parameters.items():  # pylint: disable=protected-access
                    if key.startswith(target_prefix):
                        new_param_name = re.sub(
                            '^{0}'.format(target_prefix), '', key)
                        if provider_name not in new_dict:
                            new_dict[provider_name] = {}
                        new_dict[provider_name][new_param_name] = value
                    elif not key.startswith('auto_'):
                        new_dict[key] = value
                new_config.with_dict(new_dict)

        self.proxy_provider = provider_module.Provider(new_config)
        self.proxy_provider.authenticate()

    def __getattr__(self, attr_name):
        """
        Delegate any call to any parameter/method to the underlying provider.
        Method authenticate() must have been called before.
        """
        if not self.proxy_provider:
            raise ValueError('The \'auto\' provider requires its authenticate method '
                             'to be called before any subsequent parameter/method call.')

        return getattr(self.proxy_provider, attr_name)
