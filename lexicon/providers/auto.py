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

from builtins import object

import six
import tldextract
import sys

from lexicon import providers
from lexicon.common.options_handler import env_auth_options

logger = logging.getLogger(__name__)

def _get_available_providers():
    available_providers = {}
    for _, modname, _ in pkgutil.iter_modules(providers.__path__):
        if modname != 'base' and modname != 'auto':
            try:
                available_providers[modname] = importlib.import_module('lexicon.providers.' + modname)
            except ImportError:
                logger.warn('Warning, the provider {0} cannot be loaded due to missing optional dependencies.'
                            .format(modname))

    return available_providers

AVAILABLE_PROVIDERS = _get_available_providers()

def _get_ns_records_domains_for_domain(domain):
    tlds = [tldextract.extract(ns_entry) for ns_entry in _get_ns_records_for_domain(domain)]

    return set(['{0}.{1}'.format(tld.domain, tld.suffix) for tld in tlds])

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

def _relevant_provider_for_domain(domain):
    nameserver_domains = _get_ns_records_domains_for_domain(domain)
    relevant_providers = []

    for provider_name, provider_module in AVAILABLE_PROVIDERS.items():
        ns_domains = provider_module.NAMESERVER_DOMAINS
        
        # Test plain domain string comparison
        if set([ns_domain for ns_domain in ns_domains if isinstance(ns_domain, six.string_types)]) & nameserver_domains:
            relevant_providers.append((provider_name, provider_module))
            continue

        # Test domains regexp matching
        for ns_domain in ns_domains:
            if hasattr(ns_domain, 'match') and [nameserver_domain for nameserver_domain in nameserver_domains if ns_domain.match(nameserver_domain)]:
                relevant_providers.append((provider_name, provider_module))
                continue

    if not relevant_providers:
        raise ValueError('Error, could not find the DNS provider for given domain {0}. '
                         'Found nameservers domains are {1}'.format(domain, nameserver_domains))

    if len(relevant_providers) > 1:
        logger.warn('Warning, multiple DNS providers have been found for given domain {0}, first one will be used: {1} '
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

    # Explore and load the arguments available for every provider into the 'auto' provider.
    for provider_name, provider_module in AVAILABLE_PROVIDERS.items():
        parser = argparse.ArgumentParser(add_help=False)
        provider_module.ProviderParser(parser)

        for action in parser._actions:
            action.option_strings = [re.sub(r'^--(.*)$', r'--{0}-\1'.format(provider_name), option) for option in action.option_strings]
            action.dest = 'auto_{0}_{1}'.format(provider_name, action.dest)
            subparser._add_action(action)

# Take care of the fact that this provider extends object, not BaseProvider !
# Indeed we want to delegate every parameter/method call to the delegate provider
# but __getattr__ is called only if the parameter/method cannot be found in the
# current Provider hierarchy. If it is object, it will be the case for every relevant
# call in the Lexicon library.
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
        self.domain = options.get('domain')
        self.proxy_provider = None
        self.options = options
        self.engine_overrides = engine_overrides

    def authenticate(self):
        """
        Launch the authentication process: for 'auto' provider, it means first to find the relevant
        provider, then call its authenticate() method. Almost every subsequent operation will then 
        be delegated to that provider.
        """
        mapping_override = self.options.get('mapping_override')
        mapping_override_processed = {}
        if mapping_override:
            for one_mapping in mapping_override.split(','):
                one_mapping_processed = one_mapping.split(':')
                mapping_override_processed[one_mapping_processed[0]] = one_mapping_processed[1]

        override_provider = mapping_override_processed.get(self.domain)
        if override_provider:
            provider = [element for element in AVAILABLE_PROVIDERS if element.__name__ == override_provider][0]
            logger.info('Provider authoritatively mapped for domain %s: %s.', self.domain, provider.__name__)
        else:
            (provider_name, provider_module) = _relevant_provider_for_domain(self.domain)
            logger.info('Provider discovered for domain %s: %s.', self.domain, provider_name)

        new_options = env_auth_options(provider_name)
        for key, value in self.options.items():
            target_prefix = 'auto_{0}_'.format(provider_name)
            if key.startswith(target_prefix):
                new_options[re.sub('^{0}'.format(target_prefix), '', key)] = value
            if not key.startswith('auto_'):
                new_options[key] = value

        new_options['provider_name'] = provider_name

        self.proxy_provider = provider_module.Provider(new_options, self.engine_overrides)
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
