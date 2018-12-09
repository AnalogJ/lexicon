from __future__ import absolute_import
from __future__ import unicode_literals

from contextlib import contextmanager
import hashlib
import logging
import re
import time
import requests
import six
from urllib3.util.retry import Retry

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

# Lexicon Hetzner Provider
#
# Author: Brian Rimek, 2018
#
# Implementation notes:
# * Hetzner Robot and Hetzner KonsoleH does not assign a unique identifier to each record
#   in the way that Lexicon expects. We work around this by creating an ID based on the record
#   type, name(FQDN) and content(if possible FQDN), which when taken together are unique.
#   Supported record identifier formats are:
#   * hash - generated|verified by 'list' command; e.g. '30fa112'
#   * raw  - concatenation of the record type, name(FQDN) and content(if possible FQDN)
#            with delimiter '/';
#            e.g. 'TXT/example.com./challengetoken' or 'SRV/example.com./0 0 443 msx.example.com.'

NAMESERVER_DOMAINS = []

def ProviderParser(subparser):
    subparser.add_argument('--auth-account',
                           help='specify type of Hetzner account: by default Hetzner Robot '
                           '(robot) or Hetzner KonsoleH (konsoleh)')
    subparser.add_argument('--auth-username', help='specify username of Hetzner account')
    subparser.add_argument('--auth-password', help='specify password of Hetzner account')
    subparser.add_argument('--concatenate',
                           help='use existent CNAME as record name for create|update|delete '
                           'action: by default (yes); Restriction: Only enabled if the record '
                           'name or the raw FQDN record identifier \'type/name/content\' is '
                           'specified, and additionally for update action the record name '
                           'remains the same',
                           default=str('yes'),
                           choices=['yes', 'no'])
    subparser.add_argument('--propagated',
                           help='wait until record is propagated after succeeded create|update '
                           'action: by default (yes)',
                           default=str('yes'),
                           choices=['yes', 'no'])

class Provider(BaseProvider):

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api = {
            'robot': {
                'endpoint': 'https://robot.your-server.de',
                'filter': [{'name': 'div', 'attrs': {'id': 'center_col'}}],
                'auth': {
                    'endpoint': 'https://accounts.hetzner.com',
                    'GET': {'url': '/login'},
                    'POST': {'url': '/login_check'},
                    'filter': [{'name': 'form', 'attrs': {'id': 'login-form'}}],
                    'user': '_username',
                    'pass': '_password'
                },
                'exit': {
                    'GET': {'url': '/login/logout/r/true'}
                },
                'domain_id': {
                    'GET': {'url': '/dns/index/page/<index>'},
                    'filter': [
                        {'name': 'div', 'attrs': {'id': 'center_col'}},
                        {'name': 'table', 'attrs': {'class': 'box_title'}}
                    ],
                    'domain': [{'name': 'td', 'attrs': {'class': 'title'}}],
                    'id': {'attr': 'onclick', 'regex': r'\'(\d+)\''}
                },
                'zone': {
                    'GET': [{'url': '/dns/update/id/<id>'}],
                    'POST': {'url': '/dns/update'},
                    'filter': [
                        {'name': 'div', 'attrs': {'id': 'center_col'}},
                        {'name': 'ul', 'attrs': {'class': 'error_list'}}
                    ],
                    'file': 'zonefile'
                }
            },
            'konsoleh': {
                'endpoint': 'https://konsoleh.your-server.de',
                'filter': [{'name': 'div', 'attrs': {'id': 'content'}}],
                'auth': {
                    'GET': {},
                    'POST': {'url': '/login.php'},
                    'filter': [{'name': 'form', 'attrs': {'id': 'loginform'}}],
                    'user': 'login_user_inputbox',
                    'pass': 'login_pass_inputbox'
                },
                'exit': {
                    'GET': {'url': '/logout.php'}
                },
                'domain_id': {
                    'GET': {'params': {'page': '<index>'}},
                    'filter': [
                        {'name': 'div', 'attrs': {'id': 'domainlist'}},
                        {'name': 'dl'},
                        {'name': 'a'}
                    ],
                    'domain': [{'name': 'strong'}],
                    'id': {'attr': 'href', 'regex': r'=(D\d+)'}
                },
                'zone': {
                    'GET': [
                        {'params': {'domain_number': '<id>'}},
                        {'url': '/dns.php', 'params': {'dnsaction2': 'editintextarea'}}
                    ],
                    'POST': {'url': '/dns.php'},
                    'filter': [
                        {'name': 'div', 'attrs': {'id': 'content'}},
                        {'name': 'div', 'attrs': {'class': 'error'}}
                    ],
                    'file': 'zone_file1'
                }
            }
        }

        self.account = self._get_provider_option('auth_account') 
        if self.account in (None, 'robot', 'konsoleh'):
            self.account = self.account if self.account else 'robot'
        else:
            LOGGER.error('Hetzner => Argument for --auth-account is invalid: \'%s\' '
                         '(choose from \'robot\' or \'konsoleh\')',
                         self._get_provider_option('auth_account'))
            raise AssertionError
        self.username = self._get_provider_option('auth_username')
        assert self.username is not None
        self.password = self._get_provider_option('auth_password')
        assert self.password is not None

        self.nameservers = None
        self.cname = None
        self.session = None
        self.zone = None

    # Authenticate against provider.
    def authenticate(self):
        name, concatenate = self._concatenate()
        self.domain, self.nameservers, self.cname = self._get_dns_cname(self.domain, name,
                                                                        concatenate)
        self.session = self._auth_session(self.username, self.password)
        with self._exit_session(False):
            self.domain_id = self._get_domain_id(self.domain)
            self.zone = self._get_zone(self.domain, self.domain_id)

    # Create record. If record already exists with the same content, do nothing.
    def create_record(self, type, name, content):
        with self._exit_session():
            if type is None or name is None or content is None:
                LOGGER.error('Hetzner => Record has no type|name|content specified')
                return False

            rrset = self.zone['data'].get_rdataset((self.cname if self.cname
                                                    else self._fqdn_name(name)),
                                                rdtype=type, create=True)
            for rdata in rrset:
                if self._wellformed_content(type, content) == rdata.to_text():
                    LOGGER.info('Hetzner => Record with content \'%s\' already exists',
                                content)
                    return True

            ttl = (rrset.ttl if rrset.ttl > 0
                   and rrset.ttl < self._get_lexicon_option('ttl')
                   else self._get_lexicon_option('ttl'))
            rdataset = dns.rdataset.from_text(rrset.rdclass, rrset.rdtype,
                                            ttl, self._wellformed_content(type, content))
            rrset.update(rdataset)
            synced_change = self._post_zone()
            if synced_change:
                self._propagated(type, name, content)
            return synced_change

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        with self._exit_session():
            return self._list_records(type, name, content)

    # Update a record.
    # If record does not exist or lookup matching more than one record, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type and name.
    # Support existent CNAME as record name if:
    # * record type & record name or raw FQDN record identifier 'type/name/content' are specified
    # * record name remains the same
    def update_record(self, identifier=None, type=None, name=None, content=None):
        with self._exit_session():
            if identifier:
                delete_type, delete_name, delete_content = self._parse_identifier(identifier)
                if delete_type and delete_name and delete_content:
                    type = type if type else delete_type
                    name = name if name else delete_name
                    content = content if content else delete_content
                else:
                    LOGGER.error('Hetzner => Record with identifier \'%s\' does not exist',
                                 identifier)
                    return False

            elif type and name and content:
                delete_type, delete_name, delete_content = type, name, None
            else:
                LOGGER.error('Hetzner => Record has no type|name|content specified')
                return False

            # Delete record
            delete_records = self._list_records(delete_type, delete_name, delete_content)
            if delete_records:
                for record in delete_records:
                    delete_rrset = self.zone['data'].get_rdataset(record['name']+'.',
                                                                rdtype=record['type'])
                    keep_rdatas = []
                    for delete_rdata in delete_rrset:
                        if self._wellformed_content(record['type'],
                                                    record['content']) != delete_rdata.to_text():
                            keep_rdatas.append(delete_rdata.to_text())
                    if keep_rdatas:
                        if delete_content is None:
                            LOGGER.error('Hetzner => Record lookup matching more than one record')
                            return False

                        keep_rdataset = dns.rdataset.from_text_list(delete_rrset.rdclass,
                                                                    delete_rrset.rdtype,
                                                                    record['ttl'], keep_rdatas)
                        self.zone['data'].replace_rdataset(record['name']+'.', keep_rdataset)
                    else:
                        self.zone['data'].delete_rdataset(record['name']+'.', record['type'])
                # Create record
                rrset = self.zone['data'].get_rdataset((self.cname if self.cname
                                                        else self._fqdn_name(name)),
                                                    rdtype=type, create=True)
                synced_create_change = False
                for rdata in rrset:
                    if self._wellformed_content(type, content) == rdata.to_text():
                        LOGGER.info('Hetzner => Record with content \'%s\' already exists',
                                    content)
                        synced_create_change = True
                        break
                if not synced_create_change:
                    ttl = (rrset.ttl if rrset.ttl > 0
                           and rrset.ttl < self._get_lexicon_option('ttl')
                           else self._get_lexicon_option('ttl'))
                    renew_rdataset = dns.rdataset.from_text(rrset.rdclass, rrset.rdtype, ttl,
                                                            self._wellformed_content(type, content))
                    rrset.update(renew_rdataset)
                synced_change = self._post_zone()
                if synced_change:
                    self._propagated(type, name, content)
                return synced_change

            LOGGER.error('Hetzner => Record lookup has no matches')
            return False

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    # Support existent CNAME as record name if:
    # * record type & record name or raw FQDN record identifier 'type/name/content' are specified
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        with self._exit_session():
            if identifier:
                type, name, content = self._parse_identifier(identifier)
                if type is None or name is None or content is None:
                    LOGGER.info('Hetzner => Record with identifier \'%s\' does not exist',
                                identifier)
                    return True

            delete_records = self._list_records(type, name, content)
            if delete_records:
                for record in delete_records:
                    rrset = self.zone['data'].get_rdataset(record['name']+'.',
                                                           rdtype=record['type'])
                    rdatas = []
                    for rdata in rrset:
                        if self._wellformed_content(record['type'],
                                                    record['content']) != rdata.to_text():
                            rdatas.append(rdata.to_text())
                    if rdatas:
                        rdataset = dns.rdataset.from_text_list(rrset.rdclass, rrset.rdtype,
                                                            record['ttl'], rdatas)
                        self.zone['data'].replace_rdataset(record['name']+'.', rdataset)
                    else:
                        self.zone['data'].delete_rdataset(record['name']+'.', record['type'])
                synced_change = self._post_zone()
                return synced_change

            LOGGER.info('Hetzner => Record lookup has no matches')
            return True

    # Lexicon Helpers
    ###########################################################################
    def _list_records(self, rdtype=None, name=None, content=None):
        records = []
        rrsets = self.zone['data'].iterate_rdatasets() if self.zone else []
        for rname, rdataset in rrsets:
            rtype = dns.rdatatype.to_text(rdataset.rdtype)
            rname = rname.to_text()
            if ((not rdtype or rdtype == rtype)
                    and (not name or (self.cname if self.cname
                                    else self._fqdn_name(name)) == rname)):
                for rdata in rdataset:
                    rdata = rdata.to_text()
                    if (not content or self._wellformed_content(rtype, content) == rdata):
                        raw_rdata = self._clean_TXT_record({'type': rtype,
                                                            'content': rdata})['content']
                        data = {
                            'type': rtype,
                            'name': self._full_name(rname),
                            'ttl': int(rdataset.ttl),
                            'content': raw_rdata,
                            'id': Provider._build_identifier(rtype, rname, raw_rdata)
                        }
                        records.append(data)
        return records

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = self.session.request(action, self.api[self.account]['endpoint'] + url,
                                        params=query_params, data=data)
        response.raise_for_status()
        return response

    @staticmethod
    def _build_identifier(rdtype, name, content):
        sha256 = hashlib.sha256()
        sha256.update((rdtype + '/').encode('UTF-8'))
        sha256.update((name + '/').encode('UTF-8'))
        sha256.update(content.encode('UTF-8'))
        return sha256.hexdigest()[0:7]

    def _parse_identifier(self, identifier):
        rdtype, name, content = None, None, None
        if len(identifier) > 7:
            parts = identifier.split('/')
            rdtype, name, content = parts[0], parts[1], '/'.join(parts[2:])
        else:
            records = self._list_records()
            for record in records:
                if record['id'] == identifier:
                    rdtype, name, content = record['type'], record['name']+'.', record['content']
        return rdtype, name, content

    def _wellformed_content(self, rdtype, content):
        if rdtype == 'TXT':
            if content[0] != '"':
                content = '"' + content
            if content[-1] != '"':
                content += '"'
        if rdtype in ('CNAME', 'MX', 'NS', 'SRV'):
            if content[-1] != '.':
                content = self._fqdn_name(content)
        return content

    def _concatenate(self):
        action = self._get_lexicon_option('action')
        identifier = self._get_lexicon_option('identifier')
        rdtype = self._get_lexicon_option('type')
        name = self._get_lexicon_option('name')
        concatenate = True if self._get_provider_option('concatenate') == 'yes' else False
        name_update = name
        if identifier:
            rdtype, name, _ = self._parse_identifier(identifier)
            name_update = self._fqdn_name(name_update) if name_update else name
        if action != 'list' and rdtype and rdtype != 'CNAME' and name and concatenate:
            if action != 'update' or name == name_update:
                LOGGER.info('Hetzner => Enabled CNAME lookup, '
                            'see --concatenate option with \'lexicon hetzner --help\'')
                return name, True
        LOGGER.info('Hetzner => Disabled CNAME lookup, '
                    'see --concatenate option with \'lexicon hetzner --help\'')
        return name, False

    def _propagated(self, rdtype, name, content):
        propagated = True if self._get_provider_option('propagated') == 'yes' else False
        if propagated:
            retry, max_retry = 0, 20
            while retry < max_retry:
                for rdata in self._dns_lookup((self.cname if self.cname
                                               else self._fqdn_name(name)),
                                              rdtype, self.nameservers):
                    if self._wellformed_content(rdtype, content) == rdata.to_text():
                        return True
                retry += 1
                LOGGER.info('Hetzner => Record is not propagated, %d retries remaining - '
                            'wait 30s...', (max_retry - retry))
                time.sleep(30)
        return False

    # DNS Helpers
    ###########################################################################
    def _dns_lookup(self, qname, rdtype, nameservers=None):
        rrset = dns.rrset.from_text(qname, 0, 1, rdtype)
        try:
            resolver = dns.resolver.Resolver()
            if nameservers:
                resolver.nameservers = nameservers
            rrset = resolver.query(qname, rdtype)
            for rdata in rrset:
                LOGGER.debug('DNS Lookup => %s %s %s %s',
                             rrset.qname.to_text(), dns.rdataclass.to_text(rrset.rdclass),
                             dns.rdatatype.to_text(rrset.rdtype), rdata.to_text())
        except dns.exception.DNSException as error:
            LOGGER.debug('DNS Lookup => %s', error)
        return rrset

    def _get_dns(self, domain, name):
        qname = dns.name.from_text(name)
        nameservers = []
        rdtypes_ns = ['SOA', 'NS']
        rdtypes_ip = ['A', 'AAAA']
        while (len(qname.labels) > 2 and not nameservers): # pylint: disable=E1101
            for rdtype_ns in rdtypes_ns:
                for rdata_ns in self._dns_lookup(qname, rdtype_ns):
                    for rdtype_ip in rdtypes_ip:
                        for rdata_ip in self._dns_lookup(rdata_ns.to_text().split(' ')[0],
                                                         rdtype_ip):
                            if rdata_ip.to_text() not in nameservers:
                                nameservers.append(rdata_ip.to_text())
            qdomain = qname.to_text(True)
            qname = qname.parent()
        domain = qdomain if nameservers else domain
        LOGGER.debug('DNS Lookup => %s IN NS %s', domain+'.', ' '.join(nameservers))
        return domain, nameservers

    def _get_dns_cname(self, domain, name=None, concatenate=False):
        cname = None
        if not concatenate:
            name = self._fqdn_name(name) if name else domain+'.'
            domain, nameservers = self._get_dns(domain, name)
        else:
            concat, max_concats, name = 0, 10, self._fqdn_name(name)
            while concatenate:
                if concat >= max_concats:
                    LOGGER.error('Hetzner => Record %s has more than %d concatenated CNAME '
                                 'entries. Reduce the amount of CNAME concatenations!',
                                 name, max_concats)
                    raise AssertionError
                qname = cname if cname else name
                domain, nameservers = self._get_dns(domain, qname)
                rrset = self._dns_lookup(qname, 'CNAME')
                if rrset:
                    concat += 1
                    cname = rrset[0].to_text()
                else:
                    concatenate = False
            LOGGER.info('Hetzner => Record %s has CNAME %s', name, cname)
        return domain, nameservers, cname

    # Hetzner Helpers
    ###########################################################################
    @staticmethod
    def _extract_domain_id(string, regex):
        regex = re.compile(regex)
        match = regex.search(string)
        if not match:
            return False
        return str(match.group(1))

    @staticmethod
    def _extract_hidden_data(dom):
        input_tags = dom.find_all('input', attrs={'type': 'hidden'})
        data = {}
        for input_tag in input_tags:
            data[input_tag['name']] = input_tag['value']
        return data

    @staticmethod
    def _filter_dom(dom, filters, last_find_all=False):
        if isinstance(dom, six.string_types):
            dom = BeautifulSoup(dom, 'html.parser')
        for idx, find in enumerate(filters, start=1):
            if not dom:
                break
            name , attrs = find.get('name', None), find.get('attrs', {})
            if len(filters) == idx and last_find_all:
                dom = dom.find_all(name, attrs=attrs) if name else dom.find_all(attrs=attrs)
            else:
                dom = dom.find(name, attrs=attrs) if name else dom.find(attrs=attrs)
        return dom

    def _auth_session(self, username, password):
        api = self.api[self.account]['auth']
        endpoint = api.get('endpoint', self.api[self.account]['endpoint'])
        session = requests.Session()
        session_retries = Retry(total=10, backoff_factor=0.5)
        session_adapter = requests.adapters.HTTPAdapter(max_retries=session_retries)
        session.mount('https://', session_adapter)
        response = session.request('GET', endpoint + api['GET'].get('url', '/'))
        dom = Provider._filter_dom(response.text, api['filter'])
        data = Provider._extract_hidden_data(dom)
        data[api['user']], data[api['pass']] = username, password
        response = session.request('POST', endpoint + api['POST']['url'], data=data)
        if Provider._filter_dom(response.text, api['filter']):
            LOGGER.error('Hetzner => Unable to authenticate session with %s account \'%s\': '
                         'Invalid credentials',
                         self.account, username)
            raise AssertionError
        LOGGER.info('Hetzner => Authenticate session with %s account \'%s\'',
                    self.account, username)
        return session

    @contextmanager
    def _exit_session(self, always=True):
        try:
            yield
        except Exception as exc:
            always = True
            raise exc
        finally:
            if always and self._get_provider_option('live_tests') is None:
                api = self.api[self.account]
                response = self._get(api['exit']['GET']['url'])
                if not Provider._filter_dom(response.text, api['filter']):
                    LOGGER.info('Hetzner => Exit session')
                else:
                    LOGGER.error('Hetzner => Unable to savely exit session')
                self.session = None

    def _get_domain_id(self, domain):
        api = self.api[self.account]['domain_id']
        qdomain = dns.name.from_text(domain).to_unicode(True)
        qdomain_id, domains, last_count, page = None, {}, -1, 1
        while (last_count != len(domains) and qdomain_id is None):
            last_count = len(domains)
            request = api['GET'].copy()
            url = request.get('url', '/').replace('<index>', str(page))
            params = request.get('params', {})
            for param in params:
                params[param] = params[param].replace('<index>', str(page))
            response = self._get(url, query_params=params)
            domain_tags = Provider._filter_dom(response.text, api['filter'], True)
            for domain_tag in domain_tags:
                exp_domain_tag = dict(domain_tag.attrs)[api['id']['attr']]
                domain_id = Provider._extract_domain_id(exp_domain_tag, api['id']['regex'])
                domain = (Provider._filter_dom(domain_tag, api['domain'])
                          .renderContents().decode('UTF-8'))
                domains[domain] = domain_id
                if domain == qdomain:
                    qdomain_id = domain_id
                    break
            page += 1
        if qdomain_id is None:
            LOGGER.error('Hetzner => ID for domain %s does not exists', qdomain)
            raise AssertionError
        LOGGER.info('Hetzner => Get ID %s for domain %s', qdomain_id, qdomain)
        return qdomain_id

    def _get_zone(self, domain, domain_id):
        api = self.api[self.account]
        for request in api['zone']['GET']:
            request = request.copy()
            url = request.get('url', '/').replace('<id>', domain_id)
            params = request.get('params', {})
            for param in params:
                params[param] = params[param].replace('<id>', domain_id)
            response = self._get(url, query_params=params)
        dom = Provider._filter_dom(response.text, api['filter'])
        zone_file_filter = [{'name': 'textarea', 'attrs': {'name': api['zone']['file']}}]
        zone_file = Provider._filter_dom(dom, zone_file_filter).renderContents().decode('UTF-8')
        hidden = Provider._extract_hidden_data(dom)
        zone = {'data': dns.zone.from_text(zone_file, origin=domain, relativize=False),
                'hidden': hidden}
        LOGGER.info('Hetzner => Get data for domain ID %s', domain_id)
        return zone

    def _post_zone(self):
        api = self.api[self.account]['zone']
        zone = self._get_zone(self.domain, self.domain_id)
        data = zone['hidden']
        data[api['file']] = self.zone['data'].to_text(relativize=True)
        response = self._post(api['POST']['url'], data=data)
        if Provider._filter_dom(response.text, api['filter']):
            LOGGER.error('Hetzner => Unable to update data for domain ID %s: Syntax error\n\n%s',
                         self.domain_id,
                         self.zone['data'].to_text(relativize=True).decode('UTF-8'))
            self.zone = zone
            return False

        LOGGER.info('Hetzner => Update data for domain ID %s\n\n%s',
                    self.domain_id,
                    self.zone['data'].to_text(relativize=True).decode('UTF-8'))
        if self._get_provider_option('live_tests') != 'false' and self.account == 'robot':
            LOGGER.info('Hetzner => Wait 30s...')
            time.sleep(30)
        return True
