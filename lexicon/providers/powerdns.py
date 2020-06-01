"""
Lexicon PowerDNS Provider

Author: Will Hughes, 2017

API Docs: https://doc.powerdns.com/md/httpapi/api_spec/

Implementation notes:
* The PowerDNS API does not assign a unique identifier to each record in the way
that Lexicon expects. We work around this by creating an ID based on the record
name, type and content, which when taken together are always unique
* The PowerDNS API has no notion of 'create a single record' or 'delete a single
record'. All operations are either 'replace the RRSet with this new set of records'
or 'delete all records for this name and type. Similarly, there is no notion of
'change the content of this record', because records are identified by their name,
type and content.
* The API is very picky about the format of values used when creating records:
** CNAMEs must be fully qualified
** TXT, LOC records must be quoted
This is why the _clean_content and _unclean_content methods exist, to convert
back and forth between the format PowerDNS expects, and the format Lexicon uses
"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = []


def provider_parser(subparser):
    """Configure provider parser for powerdns"""
    subparser.add_argument(
        "--auth-token", help="specify token for authentication")
    subparser.add_argument("--pdns-server", help="URI for PowerDNS server")
    subparser.add_argument(
        "--pdns-server-id", help="Server ID to interact with")
    subparser.add_argument(
        "--pdns-disable-notify", help="Disable slave notifications from master")

class Provider(BaseProvider):
    """Provider class for PowerDNS"""
    def __init__(self, config):
        super(Provider, self).__init__(config)

        self.api_endpoint = self._get_provider_option('pdns_server')
        self.disable_slave_notify = self._get_provider_option('pdns-disable-notify')

        if self.api_endpoint.endswith('/'):
            self.api_endpoint = self.api_endpoint[:-1]

        if not self.api_endpoint.endswith("/api/v1"):
            self.api_endpoint += "/api/v1"

        self.server_id = self._get_provider_option('pdns_server_id')
        if self.server_id is None:
            self.server_id = 'localhost'

        self.api_endpoint += "/servers/" + self.server_id

        self.api_key = self._get_provider_option('auth_token')
        assert self.api_key is not None
        self._zone_data = None

    def notify_slaves(self):
        """Checks to see if slaves should be notified, and notifies them if needed"""
        if self.disable_slave_notify is not None:
            LOGGER.debug('Slave notifications disabled')
            return False

        if self.zone_data()['kind'] == 'Master':
            response_code = self._put('/zones/' + self.domain + '/notify').status_code
            if response_code == 200:
                LOGGER.debug('Slave(s) notified')
                return True
            LOGGER.debug('Slave notification failed with code %i', response_code)
        else:
            LOGGER.debug('Zone type should be \'Master\' for slave notifications')
        return False

    def zone_data(self):
        """Get zone data"""
        if self._zone_data is None:
            self._zone_data = self._get('/zones/' + self._ensure_dot(self.domain)).json()
        return self._zone_data

    def _authenticate(self):
        self.zone_data()
        self.domain_id = self.domain

    def _make_identifier(self, rtype, name, content):  # pylint: disable=no-self-use
        return "{}/{}={}".format(rtype, name, content)

    def _parse_identifier(self, identifier):  # pylint: disable=no-self-use
        parts = identifier.split('/')
        rtype = parts[0]
        parts = parts[1].split('=')
        name = parts[0]
        content = "=".join(parts[1:])
        return rtype, name, content

    def _list_records(self, rtype=None, name=None, content=None):
        records = []
        for rrset in self.zone_data()['rrsets']:
            if (name is None or self._fqdn_name(rrset['name']) == self._fqdn_name(
                    name)) and (rtype is None or rrset['type'] == rtype):
                for record in rrset['records']:
                    if content is None or record['content'] == self._clean_content(rtype, content):
                        records.append({
                            'type': rrset['type'],
                            'name': self._full_name(rrset['name']),
                            'ttl': rrset['ttl'],
                            'content': self._unclean_content(rrset['type'], record['content']),
                            'id': self._make_identifier(rrset['type'],
                                                        rrset['name'], record['content'])
                        })
        LOGGER.debug('list_records: %s', records)
        return records

    def _clean_content(self, rtype, content):
        if rtype in ("TXT", "LOC"):
            if content[0] != '"':
                content = '"' + content
            if content[-1] != '"':
                content += '"'
        elif rtype == "CNAME":
            content = self._fqdn_name(content)
        return content

    def _unclean_content(self, rtype, content):
        if rtype in ("TXT", "LOC"):
            content = content.strip('"')
        elif rtype == "CNAME":
            content = self._full_name(content)
        return content

    def _create_record(self, rtype, name, content):
        rname = self._fqdn_name(name)
        newcontent = self._clean_content(rtype, content)

        updated_data = {
            'name': rname,
            'type': rtype,
            'records': [],
            'ttl': self._get_lexicon_option('ttl') or 600,
            'changetype': 'REPLACE'
        }

        updated_data['records'].append({'content': newcontent, 'disabled': False})

        for rrset in self.zone_data()['rrsets']:
            if rrset['name'] == rname and rrset['type'] == rtype:
                updated_data['ttl'] = rrset['ttl']

                for record in rrset['records']:
                    if record['content'] != newcontent:
                        updated_data['records'].append(
                            {
                                'content': record['content'],
                                'disabled': record['disabled']
                            })
                break

        request = {'rrsets': [updated_data]}
        LOGGER.debug('request: %s', request)

        self._patch('/zones/' + self._ensure_dot(self.domain), data=request)
        self.notify_slaves()
        self._zone_data = None
        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier is not None:
            rtype, name, content = self._parse_identifier(identifier)

        LOGGER.debug("delete %s %s %s", rtype, name, content)
        if rtype is None or name is None:
            raise Exception("Must specify at least both rtype and name")

        for rrset in self.zone_data()['rrsets']:
            if rrset['type'] == rtype and self._fqdn_name(rrset['name']) == self._fqdn_name(name):
                update_data = rrset

                if 'comments' in update_data:
                    del update_data['comments']

                if content is None:
                    update_data['records'] = []
                    update_data['changetype'] = 'DELETE'
                else:
                    new_record_list = []
                    for record in update_data['records']:
                        if self._clean_content(rrset['type'], content) != record['content']:
                            new_record_list.append(record)

                    update_data['records'] = new_record_list
                    update_data['changetype'] = 'REPLACE'
                break

        request = {'rrsets': [update_data]}
        LOGGER.debug('request: %s', request)

        self._patch('/zones/' + self._ensure_dot(self.domain), data=request)
        self.notify_slaves()

        self._zone_data = None
        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        self._delete_record(identifier)
        return self._create_record(rtype, name, content)

    def _patch(self, url='/', data=None, query_params=None):
        return self._request('PATCH', url, data=data, query_params=query_params)

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = requests.request(action, self.api_endpoint + url, params=query_params,
                                    data=json.dumps(data),
                                    headers={
                                        'X-API-Key': self.api_key,
                                        'Content-Type': 'application/json'
                                    })
        LOGGER.debug('response: %s', response.text)
        response.raise_for_status()
        return response

    @classmethod
    def _ensure_dot(cls, text):
        """
        This function makes sure a string contains a dot at the end
        """
        if text.endswith("."):
            return text
        return text + "."
