#!/usr/bin/env python
import argparse
import os
import importlib
import sys
from client import Client
import pkg_resources
#based off https://docs.python.org/2/howto/argparse.html


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
    parser.add_argument('--version', help="show the current version of lexicon", action='version', version='%(prog)s {0}'.format(pkg_resources.get_distribution("dns-lexicon").version))
    subparsers = parser.add_subparsers(dest='provider_name', help='specify the DNS provider to use')

    for provider in providers:
        provider_module = importlib.import_module('lexicon.providers.' + provider)
        provider_parser = getattr(provider_module, 'ProviderParser')

        subparser = subparsers.add_parser(provider, help='{0} provider'.format(provider), parents=[BaseProviderParser()])
        provider_parser(subparser)

    return parser

#dynamically determine all the providers available.
def main():
    parsed_args = MainParser().parse_args()
    print parsed_args
    client = Client(parsed_args.__dict__)
    client.execute()


if __name__ == '__main__':
    main()
