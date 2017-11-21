from __future__ import absolute_import
from __future__ import print_function

import logging
from xml.etree import ElementTree


import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

APIENDPOINTS = {
        'zonomi': 'https://zonomi.com/app',
        'rimuhosting' : 'https://rimuhosting.com'
}



# Lexicon PowerDNS Provider
#
# Author: Juan Rossi, 2017
#
# API Docs: https://zonomi.com/app/dns/dyndns.jsp
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
# * The API is very picky about the format of values used when creating records:
# ** CNAMEs must be fully qualified
# ** TXT, LOC records must be quoted
#   This is why the _clean_content and _unclean_content methods exist, to convert
#   back and forth between the format PowerDNS expects, and the format Lexicon uses


def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify token used authenticate")
    subparser.add_argument("--endpoint", help="Use Zonomi or Rimuhosting API", choices=[
        'zonomi', 'rimuhosting' ])


class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None

        if not self.options.get('auth_token'):
            raise Exception('Error, application key is not defined')

        self.api_key = self.options.get('auth_token')

        if not self.options.get('endpoint'):
            self.api_endpoint = self.engine_overrides.get('api_endpoint', APIENDPOINTS.get('zonomi'))
        else:
            self.api_endpoint = self.engine_overrides.get('api_endpoint', APIENDPOINTS.get(self.options.get('endpoint')))


    def authenticate(self):

        payload = self._get('/dns/dyndns.jsp', {
            'action' : 'QUERY',
            'name': "**." + self.options['domain'],
        })
        #print payload
        #if not payload['result']:
        #    raise Exception('No domain found')
        #if len(payload['result']) > 1:
        #    raise Exception('Too many domains found. This should not happen')

        self.domain_id = self.options['domain']

    def _make_identifier(self, type, name, content):
        return "{}/{}={}".format(type, name, content)

    def _parse_identifier(self, identifier):
        parts = identifier.split('/')
        type = parts[0]
        parts = parts[1].split('=')
        name = parts[0]
        content = "=".join(parts[1:])
        return type, name, content


    def create_record(self, type, name, content):
        data = {'action': 'SET', 'type': type, 'name': self._full_name(name), 'value': content}
        if self.options.get('ttl'):
            data['ttl'] = self.options.get('ttl')
        payload = self._get('/dns/dyndns.jsp', data)

        #logger.debug('create_record: %s', payload['success'])
        #return payload['success']


#
#    def list_records(self, type=None, name=None, content=None):
#        records = []
#        for rrset in self.zone_data()['rrsets']:
#            if (name is None or self._fqdn_name(rrset['name']) == self._fqdn_name(name)) and (type is None or rrset['type'] == type):
#                for record in rrset['records']:
#                    if content is None or record['content'] == self._clean_content(type, content):
#                        records.append({
#                            'type': rrset['type'],
#                            'name': self._full_name(rrset['name']),
#                            'ttl': rrset['ttl'],
#                            'content': self._unclean_content(rrset['type'], record['content']),
#                            'id': self._make_identifier(rrset['type'], rrset['name'], record['content'])
#                        })
#        logger.debug('list_records: %s', records)
#        return records
#
#    def _clean_content(self, type, content):
#        if type in ("TXT", "LOC"):
#            if content[0] != '"':
#                content = '"' + content
#            if content[-1] != '"':
#                content += '"'
#        elif type == "CNAME":
#            content = self._fqdn_name(content)
#        return content
#
#    def _unclean_content(self, type, content):
#        if type in ("TXT", "LOC"):
#            content = content.strip('"')
#        elif type == "CNAME":
#            content = self._full_name(content)
#        return content
#
#    def create_record(self, type, name, content):
#        content = self._clean_content(type, content)
#        for rrset in self.zone_data()['rrsets']:
#            if rrset['name'] == name and rrset['type'] == type:
#                update_data = rrset
#                if 'comments' in update_data:
#                    del update_data['comments']
#                update_data['changetype'] = 'REPLACE'
#                break
#        else:
#            update_data = {
#                'name': name,
#                'type': type,
#                'records': [],
#                'ttl': self.options.get('ttl', 600),
#                'changetype': 'REPLACE'
#            }
#
#        for record in update_data['records']:
#            if record['content'] == content:
#                return True
#
#        update_data['records'].append({
#            'content': content,
#            'disabled': False
#        })
#
#        update_data['name'] = self._fqdn_name(update_data['name'])
#
#        request = {'rrsets': [update_data]}
#        logger.debug('request: %s', request)
#
#        self._patch('/zones/' + self.options['domain'], data=request)
#        self._zone_data = None
#        return True
#
#    def delete_record(self, identifier=None, type=None, name=None, content=None):
#        if identifier is not None:
#            type, name, content = self._parse_identifier(identifier)
#
#        logger.debug("delete %s %s %s", type, name, content)
#        if type is None or name is None:
#            raise Exception("Must specify at least both type and name")
#
#        for rrset in self.zone_data()['rrsets']:
#            if rrset['type'] == type and self._fqdn_name(rrset['name']) == self._fqdn_name(name):
#                update_data = rrset
#                if 'comments' in update_data:
#                    del update_data['comments']
#                update_data['changetype'] = 'REPLACE'
#                break
#        else:
#            return True
#
#        new_records = []
#        for record in update_data['records']:
#            if content is None or self._unclean_content(type, record['content']) != self._unclean_content(type, content):
#                new_records.append(record)
#
#        update_data['name'] = self._fqdn_name(update_data['name'])
#        update_data['records'] = new_records
#
#        request = {'rrsets': [update_data]}
#        logger.debug('request: %s', request)
#
#        self._patch('/zones/' + self.options['domain'], data=request)
#        self._zone_data = None
#        return True
#
#    def update_record(self, identifier, type=None, name=None, content=None):
#        self.delete_record(identifier)
#        return self.create_record(type, name, content)
#
    def _patch(self, url='/', data=None, query_params=None):
        return self._request('PATCH', url, data=data, query_params=query_params)

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        else:
            query_params.update({'api_key': self.api_key})

        r = requests.request(action, self.api_endpoint + url, params=query_params)
        logger.debug('response: %s', r.text)
        r.raise_for_status()
        tree = ElementTree.ElementTree(ElementTree.fromstring(r.content))
        root = tree.getroot()

        return r
