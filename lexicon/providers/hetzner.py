from __future__ import absolute_import
from __future__ import unicode_literals

import hashlib
import logging
import re
import time
import requests

# Due to optional requirement
try:
    from bs4 import BeautifulSoup
    import dns.exception
    import dns.resolver
    import dns.zone
except ImportError:
    pass

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

# Lexicon Hetzner Robot Provider
#
# Author: Brian Rimek, 2018
#
# Implementation notes:
# * The Hetzner Robot does not assign a unique identifier to each record in the way
#   that Lexicon expects. We work around this by creating an ID based on the record
#   type, name(FQDN) and content(if possible FQDN), which when taken together are unique.
#   Supported record identifier formats are:
#   * hash - generated|verified by 'list' command; e.g. '30fa112'
#   * raw  - concatenation of the record type, name(FQDN) and content(if possible FQDN) 
#            with delimiter '/';
#            e.g. 'TXT/example.com./challengetoken' or 'SRV/example.com./0 0 443 msx.example.com.'

NAMESERVER_DOMAINS = []

def ProviderParser(subparser):
    subparser.add_argument('--auth-username', help='specify Hetzner Robot username')
    subparser.add_argument('--auth-password', help='specify Hetzner Robot password')
    subparser.add_argument('--concatenate',
        help='use existent CNAME as record name for create|update|delete action: by default (yes); '
        'Restriction: Only enabled if the record name or the raw FQDN record identifier '
        '\'type/name/content\' is spezified, and additionally for update action the record name '
        'remains the same',
        default='yes'.encode('UTF-8'), choices=['yes'.encode('UTF-8'), 'no'.encode('UTF-8')])
    subparser.add_argument('--propagated',
        help='wait until record is propagated after succeeded create|update action: by default (yes)',
        default='yes'.encode('UTF-8'), choices=['yes'.encode('UTF-8'), 'no'.encode('UTF-8')])

class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = 'https://robot.your-server.de'
        self.auth_endpoint = 'https://accounts.hetzner.com'

        self.username = self._get_provider_option('auth_username')
        assert self.username is not None
        self.password = self._get_provider_option('auth_password')
        assert self.password is not None

        self.nameservers = []
        self.cname = None
        self.session = None
        self.zone = None

    # Authenticate against provider.
    def authenticate(self):
        concatenate, name = self._concatenate()
        zone, self.nameservers, self.cname = self._dns_cname(concatenate, self.domain, name)
        self.session = self._open_session(self.username, self.password)
        self.domain_id = self._get_zone_id(zone)
        self.zone = self._get_zone(zone, self.domain_id)

    # Create record. If record already exists with the same content, do nothing.
    def create_record(self, type, name, content):
        if type is None or name is None or content is None:
            LOGGER.error('Hetzner => Record has no type|name|content spezified')
            self._close_session()
            return False

        rrset = self.zone['data'].get_rdataset((self.cname if self.cname else self._fqdn_name(name)), rdtype=type, create=True)
        for rdata in rrset:
            if self._wellformed_content(type, content) == rdata.to_text():
                LOGGER.info('Hetzner => Record with content \'{0}\' already exists'.format(content))
                self._close_session()
                return True

        ttl = rrset.ttl if rrset.ttl > 0 and rrset.ttl < self._get_lexicon_option('ttl') else self._get_lexicon_option('ttl')
        rdataset = dns.rdataset.from_text(rrset.rdclass, rrset.rdtype, ttl, self._wellformed_content(type, content))
        rrset.update(rdataset)
        synced_change = self._post_zone()
        if synced_change:
            self._propagated(type, name, content)
        self._close_session()
        return synced_change

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        records = []
        rrsets = self.zone['data'].iterate_rdatasets() if self.zone else []
        for rname, rdataset in rrsets:
            rtype = dns.rdatatype.to_text(rdataset.rdtype)
            rname = rname.to_text()
            if (not type or type == rtype) and (not name or (self.cname if self.cname else self._fqdn_name(name)) == rname):
                for rdata in rdataset:
                    rdata = rdata.to_text()
                    if (not content or self._wellformed_content(rtype, content) == rdata):
                        raw_rdata = self._raw_content(rtype, rdata)
                        data = {
                            'type': rtype,
                            'name': self._full_name(rname),
                            'ttl': int(rdataset.ttl),
                            'content': raw_rdata,
                            'id': self._build_identifier(rtype, rname, raw_rdata)
                        }
                        records.append(data)
        if self._get_lexicon_option('action') == 'list':
            self._close_session()
        return records

    # Update a record.
    # If record does not exist or lookup matching more than one record, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type and name.
    # Support existent CNAME as record name if:
    # * record type & record name or raw FQDN record identifier 'type/name/content' are spezified
    # * record name remains the same
    def update_record(self, identifier=None, type=None, name=None, content=None):
        if identifier:
            delete_type, delete_name, delete_content = self._parse_identifier(identifier)
            if delete_type and delete_name and delete_content:
                type = type if type else delete_type
                name = name if name else delete_name
                content = content if content else delete_content
            else:
                LOGGER.error('Hetzner => Record with identifier \'{0}\' does not exist'.format(identifier))
                self._close_session()
                return False

        elif type and name and content:
            delete_type, delete_name, delete_content = type, name, None
        else:
            LOGGER.error('Hetzner => Record has no type|name|content spezified')
            self._close_session()
            return False

        # Delete record
        delete_records = self.list_records(delete_type, delete_name, delete_content)
        if len(delete_records) > 0:
            for record in delete_records:
                delete_rrset = self.zone['data'].get_rdataset(record['name']+'.', rdtype=record['type'])
                keep_rdatas = []
                for delete_rdata in delete_rrset:
                    if self._wellformed_content(record['type'], record['content']) != delete_rdata.to_text():
                        keep_rdatas.append(delete_rdata.to_text())
                if len(keep_rdatas) > 0:
                    if delete_content is None:
                        LOGGER.error('Hetzner => Record lookup matching more than one record')
                        self._close_session()
                        return False

                    else:
                        keep_rdataset = dns.rdataset.from_text_list(delete_rrset.rdclass, delete_rrset.rdtype, record['ttl'], keep_rdatas)
                        self.zone['data'].replace_rdataset(record['name']+'.', keep_rdataset)
                else:
                    self.zone['data'].delete_rdataset(record['name']+'.', record['type'])
            # Create record
            rrset = self.zone['data'].get_rdataset((self.cname if self.cname else self._fqdn_name(name)), rdtype=type, create=True)
            synced_create_change = False
            for rdata in rrset:
                if self._wellformed_content(type, content) == rdata.to_text():
                    LOGGER.info('Hetzner => Record with content \'{0}\' already exists'.format(content))
                    synced_create_change = True
                    break
            if not synced_create_change:
                ttl = rrset.ttl if rrset.ttl > 0 and rrset.ttl < self._get_lexicon_option('ttl') else self._get_lexicon_option('ttl')
                renew_rdataset = dns.rdataset.from_text(rrset.rdclass, rrset.rdtype, ttl, self._wellformed_content(type, content))
                rrset.update(renew_rdataset)
            synced_change = self._post_zone()
            if synced_change:
                self._propagated(type, name, content)
            self._close_session()
            return synced_change

        LOGGER.error('Hetzner => Record lookup has no matches')
        self._close_session()
        return False

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    # Support existent CNAME as record name if:
    # * record type & record name or raw FQDN record identifier 'type/name/content' are spezified
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if identifier:
            type, name, content = self._parse_identifier(identifier)
            if type is None or name is None or content is None:
                LOGGER.info('Hetzner => Record with identifier \'{0}\' does not exist'.format(identifier))
                self._close_session()
                return True

        delete_records = self.list_records(type, name, content)
        if len(delete_records) > 0:
            for record in delete_records:
                rrset = self.zone['data'].get_rdataset(record['name']+'.', rdtype=record['type'])
                rdatas = []
                for rdata in rrset:
                    if self._wellformed_content(record['type'], record['content']) != rdata.to_text():
                        rdatas.append(rdata.to_text())
                if len(rdatas) > 0:
                    rdataset = dns.rdataset.from_text_list(rrset.rdclass, rrset.rdtype, record['ttl'], rdatas)
                    self.zone['data'].replace_rdataset(record['name']+'.', rdataset)
                else:
                    self.zone['data'].delete_rdataset(record['name']+'.', record['type'])
            synced_change = self._post_zone()
            self._close_session()
            return synced_change

        LOGGER.info('Hetzner => Record lookup has no matches')
        self._close_session()
        return True

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        for retry in range(10):
            try:
                response = self.session.request(action, self.api_endpoint + url, params=query_params, data=data)
                response.raise_for_status()
                return response
            except requests.exceptions.ConnectionError:
                time.sleep(1)
        raise requests.exceptions.ConnectionError
        return None

    def _build_identifier(self, type, name, content):
        sha256 = hashlib.sha256()
        sha256.update((type + '/').encode('UTF-8'))
        sha256.update((name + '/').encode('UTF-8'))
        sha256.update(content.encode('UTF-8'))
        return sha256.hexdigest()[0:7]

    def _parse_identifier(self, identifier):
        type, name, content = None, None, None
        if len(identifier) > 7:
            parts = identifier.split('/')
            type, name, content = parts[0], parts[1], '/'.join(parts[2:])
        else:
            records = self.list_records()
            for record in records:
                if record['id'] == identifier:
                    type, name, content = record['type'], record['name']+'.', record['content']
        return type, name, content

    def _wellformed_content(self, type, content):
        if type in ('TXT', 'LOC'):
            if content[0] != '"':
                content = '"' + content
            if content[-1] != '"':
                content += '"'
        if type in ('CNAME', 'MX', 'NS', 'SRV'):
            if content[-1] != '.':
                content = self._fqdn_name(content)
        return content

    def _raw_content(self, type, content):
        if type in ('TXT', 'LOC'):
            content = content.strip('"')
        return content

    def _concatenate(self):
        action = self._get_lexicon_option('action')
        identifier = self._get_lexicon_option('identifier')
        type = self._get_lexicon_option('type')
        name = self._get_lexicon_option('name')
        concatenate = True if self._get_provider_option('concatenate') == 'yes' else False
        name_update = name
        if identifier:
            type, name, content = self._parse_identifier(identifier)
            name_update = name if name_update is None or name_update == name else name_update
        if action == 'list' or (action == 'update' and name != name_update) or type is None or type == 'CNAME' or name is None or not concatenate:
            LOGGER.info('Hetzner => Disabled CNAME lookup, see --concatenate option with \'lexicon hetzner --help\'')
            return False, name

        LOGGER.info('Hetzner => Enabled CNAME lookup, see --concatenate option with \'lexicon hetzner --help\'')
        return True, name

    def _propagated(self, type, name, content):
        propagated = True if self._get_provider_option('propagated') == 'yes' else False
        if propagated:
            retry, max_retry = 0, 30
            while retry < max_retry:
                for rdata in self._dns_lookup((self.cname if self.cname else self._fqdn_name(name)), type, self.nameservers):
                    if self._wellformed_content(type, content) == rdata.to_text():
                        return True

                retry += 1
                LOGGER.info('Hetzner => Record is not propagated, {0} retries remaining - wait 30s...'.format(max_retry - retry))
                time.sleep(30)
        return False

    def _dns_lookup(self, qname, rdtype, nameservers=[]):
        if len(nameservers) == 0:
            nameservers = ['8.8.8.8', '8.8.4.4']
        rrset = dns.rrset.from_text(qname, 0, 1, rdtype)
        try:
            resolver = dns.resolver.Resolver()
            resolver.nameservers = nameservers
            rrset = resolver.query(qname, rdtype)
            for rdata in rrset:
                LOGGER.debug('DNS Lookup => {0} {1} {2} {3}'.format(rrset.qname.to_text(), dns.rdataclass.to_text(rrset.rdclass), dns.rdatatype.to_text(rrset.rdtype), rdata.to_text()))
        except dns.exception.DNSException as e:
            LOGGER.debug('DNS Lookup => {0}'.format(e))
        return rrset

    def _dns(self, zone, name):
        qname = dns.name.from_text(name)
        nameservers = []
        rdtypes_ns = ['SOA', 'NS']
        rdtypes_ip = ['A', 'AAAA']
        while (len(qname.labels) > 2 and len(nameservers) == 0):
            for rdtype_ns in rdtypes_ns:
                for rdata_ns in self._dns_lookup(qname, rdtype_ns):
                    for rdtype_ip in rdtypes_ip:
                        for rdata_ip in self._dns_lookup(rdata_ns.to_text().split(' ')[0], rdtype_ip):
                            if rdata_ip.to_text() not in nameservers:
                                nameservers.append(rdata_ip.to_text())
            qzone = qname.to_text()
            qname = qname.parent()
        zone = qzone if len(nameservers) > 0 else zone
        nameservers = nameservers if len(nameservers) > 0 else []
        LOGGER.debug('DNS Lookup => {0} IN NS {1}'.format(zone, ' '.join(nameservers)))
        return zone, nameservers

    def _dns_cname(self, concatenate, zone, name=None):
        cname = None
        if not concatenate:
            name = self._fqdn_name(name) if name else zone+'.'
            zone, nameservers = self._dns(zone, name)
        else:
            concat, max_concats, name = 0, 10, self._fqdn_name(name)
            while concatenate == True:
                if concat >= max_concats:
                    LOGGER.error('Hetzner => Record {0} has more than {1} concatenated CNAME entries. Reduce the amount of CNAME concatenations!'.format(name, max_concats))
                    self._close_session()
                    raise AssertionError
                qname = cname if cname else name
                zone, nameservers = self._dns(zone, qname)
                rrset = self._dns_lookup(qname, 'CNAME')
                if len(rrset) > 0:
                    concat += 1
                    cname = rrset[0].to_text()
                else:
                    concatenate = False
        LOGGER.info('Hetzner => Record {0} has CNAME {1}'.format(name, cname))
        return zone, nameservers, cname

    def _open_session(self, username, password):
        session = requests.session()
        session.request('GET', '{0}/login'.format(self.auth_endpoint))
        response = session.request('POST', '{0}/login_check'.format(self.auth_endpoint), data={'_username': username, '_password': password})
        if '{0}/account/masterdata'.format(self.auth_endpoint) == response.url and response.status_code == 200:
            response = session.request('GET', '{0}/'.format(self.api_endpoint))
        if self.api_endpoint not in response.url or response.status_code != 200:
            LOGGER.error('Hetzner => Unable to open session to account {0}'.format(username))
            raise AssertionError
        LOGGER.info('Hetzner => Open session to account {0}'.format(username))
        return session

    def _close_session(self):
        if self._get_provider_option('live_tests') is None:
            response = self._get('/login/logout/r/true')
            if '{0}/logout'.format(self.auth_endpoint) not in response.url and response.status_code != 200:
                LOGGER.error('Hetzner => Unable to safely close session')
            else:
                LOGGER.info('Hetzner => Close session')
            self.session = None

    def _extract_zone_id_from_js(self, string):
        regex = re.compile(r'\'(\d+)\'')
        match = regex.search(string)
        if not match: 
            return False
        return int(match.group(1))

    def _get_zone_id(self, zone):
        qzone_name = dns.name.from_text(zone).to_unicode(True)
        qzone_id, zones, last_count, page = None, {}, -1, 1
        while (last_count != len(zones) and qzone_id is None):
            last_count = len(zones)
            response = self._get('/dns/index/page/{0}'.format(page))
            boxes = BeautifulSoup(response.text, 'html.parser').findAll('table', attrs={'class': 'box_title'})
            for box in boxes:
                expand_box = dict(box.attrs)['onclick']
                zone_id = self._extract_zone_id_from_js(expand_box)
                zone_name = box.find('td', attrs={'class': 'title'}).renderContents().decode('UTF-8')
                zones[zone_name] = zone_id
                if zone_name == qzone_name:
                    qzone_id = zone_id
                    break
            page += 1
        if qzone_id is None:
            LOGGER.error('Hetzner => ID for zone {0} does not exists'.format(zone))
            self._close_session()
            raise AssertionError
        LOGGER.info('Hetzner => Get ID {1} for zone {0}'.format(zone, qzone_id))
        return qzone_id

    def _get_zone(self, zone_name, zone_id):
        response = self._get('/dns/update/id/{0}'.format(zone_id))
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', attrs={'id': 'csrf_token'})['value']
        zone_file = soup.find('textarea', attrs={'id': 'zonefile'}).renderContents().decode('UTF-8')
        zone = {'data': dns.zone.from_text(zone_file, origin=zone_name, relativize=False), 'token': csrf_token}
        LOGGER.info('Hetzner => Get data for zone ID {0}'.format(zone_id))
        return zone

    def _get_language(self):
        response = self._get('/preferences/culture')
        soup = BeautifulSoup(response.text, 'html.parser')
        language = (soup.find('select', attrs={'id': 'culture'})).find('option', attrs={'selected': 'selected'})['value']
        LOGGER.info('Hetzner => Get GUI language {0} for account {1}'.format(language, self.username))
        return language

    def _post_zone(self):
        language = self._get_language()
        post_response = {'de_DE': 'Vielen Dank', 'en_GB': 'Thank you for'}
        response = self._post('/dns/update', data={'id': self.domain_id, 'zonefile': self.zone['data'].to_text(relativize=True), '_csrf_token': self.zone['token']})
        # ugly: the Hetzner Robot status code is always 200 (delivering the update form as an 'error message')
        if post_response[language] in response.text:
            LOGGER.info('Hetzner => Update data for zone ID {0} - wait 30s...\n\n{1}'.format(self.domain_id, self.zone['data'].to_text(relativize=True)))
            if self._get_provider_option('live_tests') != 'false':
                time.sleep(30)
            return True

        LOGGER.error('Hetzner => Unable to update data for zone ID {0}\n\n{1}'.format(self.domain_id, self.zone['data'].to_text(relativize=True)))
        return False
