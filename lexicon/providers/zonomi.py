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
    #subparser.add_argument("--priority", help="priority")
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
            'name': "**." + self.options['domain'] })

        if payload.find('is_ok').text != 'OK:':
            raise Exception('Error with api {0}'.format(payload.find('is_ok').text))

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
        request = {
                'action': 'SET', 
                'type': type, 
                'name': self.options['domain'], 
                'value': content 
                }

        if name is not None:
            request['name'] = self._full_name(name)
 
        if self.options.get('ttl'):
            request['ttl'] = self.options.get('ttl')

        if self.options.get('priority'):
            request['prio'] = self.options.get('priority')
        
        payload = self._get('/dns/dyndns.jsp', request)
        
        logger.debug('create_record: %s', payload.find('is_ok').text)
        return payload.find('is_ok').text



    def list_records(self, type=None, name=None, content=None):
        records = []

        request = {
            'action' : 'QUERY',
            'name': "**." + self.options['domain'],
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
                'ttl': rxml.attrib['ttl'],
                'content': rxml.attrib['content'],
                'id': self._make_identifier(rxml.attrib['type'],rxml.attrib['name'],rxml.attrib['content'])
            }
            if rxml.attrib['prio']:
                processed_record['priority'] = rxml.attrib['prio']

            records.append(processed_record)
        logger.debug('list_records: %s', records)
        return records

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if identifier is not None:
            type, name, content = self._parse_identifier(identifier)
        request = {
            'action' : 'DELETE',
            'type' : type,
            'name' : self._full_name(name),
            'value': content
        }

        payload = self._get('/dns/dyndns.jsp', request)
        
        logger.debug('delete_record: %s', payload.find('is_ok').text)
        return payload.find('is_ok').text


    def update_record(self, identifier, type=None, name=None, content=None):
        
        self.delete_record(identifier)
        
        ttype, tname, tcontent = self._parse_identifier(identifier)

        request = {
                'action': 'SET', 
                'type': ttype, 
                'name': self._full_name(tname), 
                'value': tcontent 
                }

        if name:
            request['name'] = self._full_name(name)
        if content:
            request['value'] = content
        if self.options.get('ttl'):
            request['ttl'] = self.options.get('ttl')
        if self.options.get('priority'):
            request['prio'] = self.options.get('priority')

        payload = self._get('/dns/dyndns.jsp', request)

        logger.debug('update_record: %s', payload.find('is_ok').text)
        return payload.find('is_ok').text



    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        else:
            query_params['api_key'] = self.options.get('auth_token')

        r = requests.request(action, self.api_endpoint + url, params=query_params)
        logger.debug('response: %s', r.content)
        tree = ElementTree.ElementTree(ElementTree.fromstring(r.content))
        root = tree.getroot()
        if root.tag == 'error':
            raise Exception('An error occurred: {0}'.format(root.text))
        #r.raise_for_status()
        return root
