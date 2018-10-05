from __future__ import absolute_import

import subprocess
import re
import os
import pkgutil
import logging
import argparse
import importlib
import argparse
import re

import six
import tldextract
import sys

from lexicon import providers
from lexicon.common.options_handler import env_auth_options

LOGGER = logging.getLogger(__name__)

def _get_available_providers():
    available_providers = []
    for importer, modname, _ in pkgutil.iter_modules(providers.__path__):
        if modname != 'base' and modname != 'auto':
            try:
                available_providers.append(importer.find_module(modname).load_module(modname))
            except ImportError:
                LOGGER.warn('Warning, the provider {0} cannot be loaded due to missing optional dependencies.'
                            .format(modname))

    return available_providers

AVAILABLE_PROVIDERS = _get_available_providers()

def _get_ns_records_for_domain(domain):
    # Available both for Windows and Linux (if dnsutils is installed for the latter)
    try:
        output = subprocess.check_output(['nslookup', '-querytype=NS', domain],
                                        stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        if 'NXDOMAIN' in e.output:
            raise ValueError('Error, domain {0} could not be resolved.'.format(domain))

    pattern = re.compile(r'nameserver = (.*?)\.*{0}'.format(os.linesep))
    match = pattern.findall(output.decode())

    if not match:
        raise ValueError('Error, could not find ns entries for domain {0}. '
                         'Does this domain is correctly configured ?'.format(domain))

    return match

def _get_ns_records_domains_for_domain(domain):
    tlds = [tldextract.extract(ns_entry) for ns_entry in _get_ns_records_for_domain(domain)]

    return set(['{0}.{1}'.format(tld.domain, tld.suffix) for tld in tlds])

def _relevant_provider_for_domain(domain):
    nameserver_domains = _get_ns_records_domains_for_domain(domain)
    relevant_providers = []

    for provider in AVAILABLE_PROVIDERS:
        ns_domains = provider.NAMESERVER_DOMAINS
        
        # Test plain domain string comparison
        if set([ns_domain for ns_domain in ns_domains if isinstance(ns_domain, six.string_types)]) & nameserver_domains:
            relevant_providers.append(provider)
            continue

        # Test domains regexp matching
        for ns_domain in ns_domains:
            if hasattr(ns_domain, 'match') and [nameserver_domain for nameserver_domain in nameserver_domains if ns_domain.match(nameserver_domain)]:
                relevant_providers.append(provider)
                continue

    if not relevant_providers:
        raise ValueError('Error, could not find the DNS provider for given domain {0}. '
                         'Found nameservers are {1}'.format(domain, nameserver_domains))

    if len(relevant_providers) > 1:
        LOGGER.warn('Warning, multiple DNS providers have been found for given domain {0}, first one will be used: {1} '
                    'This may indicate a misconfiguration in one or more provider.'
                    .format(domain, relevant_providers))

    return relevant_providers[0]

def ProviderParser(subparser):
    subparser.description = '''
        Provider 'auto' enables the Lexicon provider auto-discovery feature.
        Based on the nameservers declared for the given domain, Lexicon will try to find the DNS provider holding the DNS zone if it is supported.
        Actual DNS zone read/write operations will be delegated to the provider found: every environment variable or command line specific to this provider can be passed to Lexicon and will be processed accordingly.
        '''
    subparser.add_argument("--mapping-override", metavar="[DOMAIN]:[PROVIDER], ...", help="comma separated list of elements in the form of [DOMAIN]:[PROVIDER] to authoritatively map a particular domain to a particular provider")

    # Explore and load the arguments available for every provider
    for provider in AVAILABLE_PROVIDERS:
        parser = argparse.ArgumentParser(add_help=False)
        provider.ProviderParser(parser)

        for action in parser._actions:
            action.option_strings = [re.sub(r'^--(.*)$', r'--{0}-\1'.format(provider.__name__), option) for option in action.option_strings]
            action.dest = 'auto_{0}_{1}'.format(provider.__name__, action.dest)
            subparser._add_action(action)

class Provider(object):
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
    def __init__(self, options, engine_overrides=None):
        domain = options.get('domain')

        mapping_override = options.get('mapping_override')
        mapping_override_processed = {}
        if mapping_override:
            for one_mapping in mapping_override.split(','):
                one_mapping_processed = one_mapping.split(':')
                mapping_override_processed[one_mapping_processed[0]] = one_mapping_processed[1]

        override_provider = mapping_override_processed.get(domain)
        if override_provider:
            provider = [element for element in AVAILABLE_PROVIDERS if element.__name__ == override_provider][0]
            LOGGER.info('Provider authoritatively mapped for domain %s: %s.', domain, provider.__name__)
        else:
            provider = _relevant_provider_for_domain(domain)
            LOGGER.info('Provider discovered for domain %s: %s.', domain, provider.__name__)

        new_options = env_auth_options(provider.__name__)
        for key, value in options.items():
            target_prefix = 'auto_{0}_'.format(provider.__name__)
            if key.startswith(target_prefix):
                new_options[re.sub('^{0}'.format(target_prefix), '', key)] = value
            if not key.startswith('auto_'):
                new_options[key] = value

        new_options['provider_name'] = provider.__name__

        self.delegate = provider.Provider(new_options, engine_overrides)

    def __getattr__(self, attr_name):
        """Delegate any call to any parameter/method to the underlying provider"""
        return getattr(self.delegate, attr_name)
