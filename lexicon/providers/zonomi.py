from __future__ import absolute_import
import logging
from xml.etree import ElementTree

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

APIENTRYPOINT = {
    'zonomi': 'https://zonomi.com/app',
    'rimuhosting': 'https://rimuhosting.com'
}

NAMESERVER_DOMAINS = ['zonomi.com']

# Lexicon Zonomi and Rimuhosting Provider
#
# Author: Juan Rossi, 2017
#
# Zonomi API Docs: https://zonomi.com/app/dns/dyndns.jsp
# Rimuhosting API Docs: https://rimuhosting.com/dns/dyndns.jsp
#
# Implementation notes:
# * Lots of tricks taken from the PowerDNS API
# * The Zonomi API does not assign a unique identifier to each record in the way
#   that Lexicon expects. We work around this by creating an ID based on the record
#   name, type and content, which when taken together are always unique
# * The  API has no notion of 'create a single record' or 'delete a single
#   record'. All operations are either 'replace the RRSet with this new set of records'
#   or 'delete all records for this name and type. Similarly, there is no notion of
#   'change the content of this record', because records are identified by their name,
#   type and content.


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")
    subparser.add_argument("--auth-entrypoint", help="use Zonomi or Rimuhosting API", choices=[
        'zonomi', 'rimuhosting'])


class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        if not self._get_provider_option('auth_token'):
            raise Exception('Error, application key is not defined')

        self.api_endpoint = APIENTRYPOINT.get('zonomi')

        if self._get_provider_option('auth_entrypoint'):
            self.api_endpoint = APIENTRYPOINT.get(
                self._get_provider_option('auth_entrypoint'))

    def authenticate(self):

        payload = self._get('/dns/dyndns.jsp', {
            'action': 'QUERY',
            'name': "**." + self.domain,
            'type': 'SOA'
        })

        if payload.find('is_ok').text != 'OK:':
            raise Exception('Error with api {0}'.format(
                payload.find('is_ok').text))

        self.domain_id = self.domain

    def _make_identifier(self, type, name, content):
        return "{}/{}={}".format(type, self._full_name(name), content)

    def _parse_identifier(self, identifier):
        parts = identifier.split('/')
        type = parts[0]
        parts = parts[1].split('=')
        name = parts[0]
        content = "=".join(parts[1:])
        return type, name, content

    def create_record(self, type, name, content):
        request = {
            'action': 'SET',
            'type': type,
            'name': self.domain,
            'value': content
        }

        if name is not None:
            request['name'] = self._full_name(name)

        if self._get_lexicon_option('ttl'):
            request['ttl'] = self._get_lexicon_option('ttl')

        if self._get_lexicon_option('priority'):
            request['prio'] = self._get_lexicon_option('priority')

        payload = self._get('/dns/dyndns.jsp', request)

        if payload.find('is_ok').text != 'OK:':
            raise Exception('An error occurred: {0}'.format(
                payload.find('is_ok').text))

        LOGGER.debug('create_record: %s', True)
        return True

    def list_records(self, type=None, name=None, content=None):
        records = []

        request = {
            'action': 'QUERY',
            'name': "**." + self.domain
        }

        if type is not None:
            request['type'] = type
        if name is not None:
            request['name'] = self._full_name(name)
        if content is not None:
            request['value'] = content

        payload = self._get('/dns/dyndns.jsp', request)
        for rxml in payload.iter('record'):
            processed_record = {
                'type': rxml.attrib['type'],
                'name': rxml.attrib['name'],
                'content': rxml.attrib['content'],
                'id': self._make_identifier(rxml.attrib['type'], rxml.attrib['name'], rxml.attrib['content']),
                'ttl': rxml.attrib['ttl'].split()[0]
            }
            records.append(processed_record)
        LOGGER.debug('list_records: %s', records)
        return records

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if identifier is not None:
            type, name, content = self._parse_identifier(identifier)

        request = {
            'action': 'DELETE',
            'name': self.domain
        }

        if type is not None:
            request['type'] = type
        if name is not None:
            request['name'] = self._full_name(name)
        if content is not None:
            request['value'] = content

        payload = self._get('/dns/dyndns.jsp', request)

        if payload.find('is_ok').text != 'OK:':
            raise Exception('An error occurred: {0}'.format(
                payload.find('is_ok').text))

        LOGGER.debug('delete_record: %s', True)
        return True

    def update_record(self, identifier, type=None, name=None, content=None):
        self.delete_record(identifier)
        ttype, tname, tcontent = self._parse_identifier(identifier)
        request = {
            'action': 'SET',
            'type': ttype,
            'name': self._full_name(tname),
            'value': tcontent
        }

        if type is not None:
            request['type'] = type
        if name is not None:
            request['name'] = self._full_name(name)
        if content is not None:
            request['value'] = content
        if self._get_lexicon_option('ttl'):
            request['ttl'] = self._get_lexicon_option('ttl')
        if self._get_lexicon_option('priority'):
            request['prio'] = self._get_lexicon_option('priority')

        payload = self._get('/dns/dyndns.jsp', request)

        if payload.find('is_ok').text != 'OK:':
            raise Exception('An error occurred: {0}'.format(
                payload.find('is_ok').text))

        LOGGER.debug('update_record: %s', True)
        return True

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        else:
            query_params['api_key'] = self._get_provider_option('auth_token')

        r = requests.request(action, self.api_endpoint +
                             url, params=query_params)
        tree = ElementTree.ElementTree(ElementTree.fromstring(r.content))
        root = tree.getroot()
        if root.tag == 'error':
            raise Exception('An error occurred: {0}'.format(root.text))
        else:
            r.raise_for_status()
        return root
