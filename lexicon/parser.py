"""Parsers definition for the Lexicon command-line interface"""
import argparse
import importlib
import pkgutil

import pkg_resources
from lexicon import providers as providers_package


def generate_base_provider_parser():
    """Function that generates the base provider to be used by all dns providers."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('action', help='specify the action to take', default='list',
                        choices=['create', 'list', 'update', 'delete'])
    parser.add_argument(
        'domain', help='specify the domain, supports subdomains as well')
    parser.add_argument('type', help='specify the entry type', default='TXT',
                        choices=['A', 'AAAA', 'CNAME', 'MX', 'NS', 'SOA', 'TXT', 'SRV', 'LOC'])

    parser.add_argument('--name', help='specify the record name')
    parser.add_argument('--content', help='specify the record content')
    parser.add_argument('--ttl', type=int,
                        help='specify the record time-to-live')
    parser.add_argument('--priority', help='specify the record priority')
    parser.add_argument(
        '--identifier', help='specify the record for update or delete actions')
    parser.add_argument('--log_level', help='specify the log level', default='ERROR',
                        choices=['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET'])
    parser.add_argument('--output',
                        help=('specify the type of output: by default a formatted table (TABLE), '
                              'a formatted table without header (TABLE-NO-HEADER), '
                              'a JSON string (JSON) or no output (QUIET)'),
                        default='TABLE', choices=['TABLE', 'TABLE-NO-HEADER', 'JSON', 'QUIET'])
    return parser


def generate_cli_main_parser():
    """Using all providers available, generate a parser that will be used by Lexicon CLI"""
    providers = []
    for _, modname, _ in pkgutil.iter_modules(providers_package.__path__):
        if modname != 'base':
            providers.append(modname)
    providers = sorted(providers)

    parser = argparse.ArgumentParser(
        description='Create, Update, Delete, List DNS entries')
    try:
        version = pkg_resources.get_distribution('dns-lexicon').version
    except pkg_resources.DistributionNotFound:
        version = 'unknown'
    parser.add_argument('--version', help='show the current version of lexicon',
                        action='version', version='%(prog)s {0}'.format(version))
    parser.add_argument('--delegated', help='specify the delegated domain')
    subparsers = parser.add_subparsers(
        dest='provider_name', help='specify the DNS provider to use')
    subparsers.required = True

    for provider in providers:
        provider_module = importlib.import_module(
            'lexicon.providers.' + provider)
        provider_parser = getattr(provider_module, 'ProviderParser')

        subparser = subparsers.add_parser(provider, help='{0} provider'.format(provider),
                                          parents=[generate_base_provider_parser()])
        provider_parser(subparser)

    return parser
