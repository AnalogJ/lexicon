#!/usr/bin/env python
from __future__ import absolute_import
from __future__ import print_function

import argparse
import importlib
import logging
import os
import sys
import json

import pkg_resources

from .client import Client

#based off https://docs.python.org/2/howto/argparse.html

logger = logging.getLogger(__name__)


def BaseProviderParser():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("action", help="specify the action to take", default='list', choices=['create', 'list', 'update', 'delete'])
    parser.add_argument("domain", help="specify the domain, supports subdomains as well")
    parser.add_argument("type", help="specify the entry type", default='TXT', choices=['A', 'AAAA', 'CNAME', 'MX', 'NS', 'SOA', 'TXT', 'SRV', 'LOC'])

    parser.add_argument("--name", help="specify the record name")
    parser.add_argument("--content", help="specify the record content")
    parser.add_argument("--ttl", type=int, help="specify the record time-to-live")
    parser.add_argument("--priority", help="specify the record priority")
    parser.add_argument("--identifier", help="specify the record for update or delete actions")
    parser.add_argument("--log_level", help="specify the log level", default="ERROR", choices=["CRITICAL","ERROR","WARNING","INFO","DEBUG","NOTSET"])
    parser.add_argument("--quiet", help="If set, do not print command result on stdout", action='store_true')
    parser.add_argument("--json", help="If set, return print command on stdout as a json string", action='store_true')
    parser.add_argument("--no-headers", help="If set, return print command without table headers", action='store_true')
    return parser

def MainParser():
    current_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'providers')
    providers = [os.path.splitext(f)[0] for f in os.listdir(current_filepath) if os.path.isfile(os.path.join(current_filepath, f))]
    providers = list(set(providers))
    providers.remove('base')
    providers.remove('__init__')
    providers = [x for x in providers if not x.startswith('.')]

    providers = sorted(providers)

    parser = argparse.ArgumentParser(description='Create, Update, Delete, List DNS entries')
    try:
        version = pkg_resources.get_distribution("dns-lexicon").version
    except pkg_resources.DistributionNotFound:
        version = 'unknown'
    parser.add_argument('--version', help="show the current version of lexicon", action='version', version='%(prog)s {0}'.format(version))
    parser.add_argument('--delegated', help="specify the delegated domain")
    subparsers = parser.add_subparsers(dest='provider_name', help='specify the DNS provider to use')
    subparsers.required = True

    for provider in providers:
        provider_module = importlib.import_module('lexicon.providers.' + provider)
        provider_parser = getattr(provider_module, 'ProviderParser')

        subparser = subparsers.add_parser(provider, help='{0} provider'.format(provider), parents=[BaseProviderParser()])
        provider_parser(subparser)

    return parser

# Print returned JSON into a nice table for command line usage
def print_json_result(logger, output=None, without_header=None):
    try:
        _ = (entry for entry in output)
    except:
        logger.debug('Command output is not iterable, and then cannot be printed with --quiet parameter not enabled.')
        return

    array = [[row['id'], row['type'], row['name'], row['content'], row['ttl']] for row in output]

    # Insert header (insert before calculating the max width of each column to take headers size into account)
    if not without_header:
        headers = ['ID', 'TYPE', 'NAME', 'CONTENT', 'TTL']
        array.insert(0, headers)

    columnWidths = [0, 0, 0, 0, 0]
    # Find max width for each column
    for row in array:
        for idx, col in enumerate(row):
            width = len(str(col))
            if width > columnWidths[idx]:
                columnWidths[idx] = width

    # Add a "nice" separator
    if not without_header:
        array.insert(1, ['-' * columnWidths[idx] for idx in range(len(columnWidths))])

    # Construct table to be printed
    print_table = []
    for row in array:
        rowList = []
        for idx, col in enumerate(row):
            rowList.append(str(col).ljust(columnWidths[idx]))
        print_table.append(' '.join(rowList))

    # Print table
    print('\n'.join(print_table))

# Dynamically determine all the providers available.
def main():
    parsed_args = MainParser().parse_args()
    log_level = logging.getLevelName(parsed_args.log_level)
    logging.basicConfig(stream=sys.stdout, level=log_level, format='%(message)s')

    logger.debug('Arguments: %s', parsed_args)
    client = Client(parsed_args.__dict__)
    
    output = client.execute()

    if not parsed_args.__dict__['quiet']:
        if not parsed_args.__dict__['json']:
            print_json_result(logger, output, parsed_args.__dict__['no_headers'])
        else:
            try:
                print(json.dumps(output))
            except:
                logger.debug('Output is not a JSON, and then cannot be printed with --json parameter enabled.')
                pass

if __name__ == '__main__':
    main()
