#!/usr/bin/env python
import argparse
import os
import sys
from client import Client
#based off https://docs.python.org/2/howto/argparse.html

#dynamically determine all the providers available.
def main():
    current_filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'providers')
    providers = [os.path.splitext(f)[0] for f in os.listdir(current_filepath) if os.path.isfile(os.path.join(current_filepath, f))]
    providers = list(set(providers))
    providers.remove('base')
    providers.remove('__init__')


    parser = argparse.ArgumentParser(description='Create, Update, Delete, List DNS entries')
    parser.add_argument("provider_name", help="specify the DNS provider to use", choices=providers)
    parser.add_argument("action", help="specify the action to take", default='list', choices=['create', 'list', 'update', 'delete'])
    parser.add_argument("domain", help="specify the domain, supports subdomains as well")
    parser.add_argument("type", help="specify the entry type", default='TXT', choices=['A', 'AAAA', 'CNAME', 'MX', 'NS', 'SPF', 'SOA', 'TXT', 'SRV', 'LOC'])

    parser.add_argument("--name", help="specify the record name")
    parser.add_argument("--content", help="specify the record content")
    parser.add_argument("--ttl", help="specify the record time-to-live")
    parser.add_argument("--priority", help="specify the record priority")
    parser.add_argument("--identifier", help="specify the record for update or delete actions")


    parser.add_argument("--auth-username", help="specify username used to authenticate to DNS provider")
    parser.add_argument("--auth-password", help="specify password used to authenticate to DNS provider")
    parser.add_argument("--auth-token", help="specify token used authenticate to DNS provider")
    parser.add_argument("--auth-otp-token", help="specify OTP/2FA token used authenticate to DNS provider")

    parsed_args = parser.parse_args()
    print parsed_args
    client = Client(parsed_args.__dict__)
    client.execute()


if __name__ == '__main__':
    main()
