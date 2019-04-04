"""Module provider for Hetzner"""
from __future__ import absolute_import
from __future__ import unicode_literals

from contextlib import contextmanager
import hashlib
import logging
import re
import time
import requests
from six import string_types
from urllib3.util.retry import Retry

# Due to optional requirement
try:
    from bs4 import BeautifulSoup
    import dns.resolver
    import dns.zone
except ImportError:
    pass

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = []


def provider_parser(subparser):
    """Configure a provider parser for Hetzner"""
    subparser.add_argument('--auth-account',
                           help='specify type of Hetzner account: by default Hetzner Robot '
                           '(robot) or Hetzner konsoleH (konsoleh)')
    subparser.add_argument('--auth-username', help='specify username of Hetzner account')
    subparser.add_argument('--auth-password', help='specify password of Hetzner account')
    subparser.add_argument('--linked',
                           help='if exists, uses linked CNAME as A|AAAA|TXT record name for edit '
                           'actions: by default (yes); Further restriction: Only enabled if '
                           'record name or raw FQDN record identifier \'type/name/content\' is '
                           'specified, and additionally for update actions the record name '
                           'remains the same',
                           default=str('yes'),
                           choices=['yes', 'no'])
    subparser.add_argument('--propagated',
                           help='waits until record is publicly propagated after succeeded '
                           'create|update actions: by default (yes)',
                           default=str('yes'),
                           choices=['yes', 'no'])
    subparser.add_argument('--latency',
                           help='specify latency, used during checks for publicly propagation '
                           'and additionally for Hetzner Robot after record edits: by default '
                           '30s (30)',
                           default=int(30),
                           type=int)


class Provider(BaseProvider):
    """
    Implements the Hetzner DNS Provider.
    There are two variants to manage DNS records on Hetzner: Hetzner Robot or
    Hetzner konsoleH. Both do not provide a common API, therefore this provider
    implements missing read and write methods in a generic way. For editing DNS
    records on Hetzner, this provider manipulates and replaces the whole DNS zone.
    Furthermore, there is no unique identifier to each record in the way that Lexicon
    expects, why this provider implements a pseudo-identifer based on the record type,
    name and content for use of the --identifier parameter. Supported identifier
    formats are:
        - hash  generated|verified by 'list' command; e.g. '30fa112'
        - raw   concatenation of the record type, name (FQDN) and content (if possible
                FQDN) with delimiter '/'; e.g. 'SRV/example.com./0 0 443 msx.example.com.'
                or 'TXT/example.com./challengetoken'
    Additional, this provider implements the option of replacing an A, AAAA or TXT record
    name with an existent linked CNAME for edit actions via the --linked parameter and
    the option of waiting until record is publicly propagated after succeeded create or
    update actions via the --propagated parameter. As further restriction, the use of a
    linked CNAME is only enabled if the record type & record name or the raw identifier are
    specified, and additionally for the update action the record name remains the same.
    """
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
        self.session = None

        self.account = self._get_provider_option('auth_account')
        if self.account in (None, 'robot', 'konsoleh'):
            self.account = self.account if self.account else 'robot'
        else:
            LOGGER.error('Hetzner => Argument for --auth-account is invalid: \'%s\' '
                         '(choose from \'robot\' or \'konsoleh\')', self.account)
            raise AssertionError
        self.username = self._get_provider_option('auth_username')
        assert self.username is not None
        self.password = self._get_provider_option('auth_password')
        assert self.password is not None

    def _authenticate(self):
        """
        Connects to Hetzner account and returns, if authentification was
        successful and the domain or CNAME target is managed by this account.
        """
        with self._session(self.domain, get_zone=False):
            return True

    def _create_record(self, rtype, name, content):
        """
        Connects to Hetzner account, adds a new record to the zone and returns a
        boolean, if creation was successful or not. Needed record rtype, name and
        content for record to create.
        """
        with self._session(self.domain, self.domain_id) as ddata:
            # Validate method parameters
            if not rtype or not name or not content:
                LOGGER.warning('Hetzner => Record has no rtype|name|content specified')
                return False

            # Add record to zone
            name = ddata['cname'] if ddata['cname'] else self._fqdn_name(name)
            rrset = ddata['zone']['data'].get_rdataset(name, rdtype=rtype, create=True)
            for rdata in rrset:
                if self._convert_content(rtype, content) == rdata.to_text():
                    LOGGER.info('Hetzner => Record with content \'%s\' already exists',
                                content)
                    return True

            ttl = (rrset.ttl if 0 < rrset.ttl < self._get_lexicon_option('ttl')
                   else self._get_lexicon_option('ttl'))
            rdataset = dns.rdataset.from_text(rrset.rdclass, rrset.rdtype,
                                              ttl, self._convert_content(rtype, content))
            rrset.update(rdataset)
            # Post zone to Hetzner
            synced_change = self._post_zone(ddata['zone'])
            if synced_change:
                self._propagated_record(rtype, name, self._convert_content(rtype, content),
                                        ddata['nameservers'])
            return synced_change

    def _list_records(self, rtype=None, name=None, content=None):
        """
        Connects to Hetzner account and returns a list of records filtered by record
        rtype, name and content. The list is empty if no records found.
        """
        with self._session(self.domain, self.domain_id) as ddata:
            name = self._fqdn_name(name) if name else None
            return self._list_records_in_zone(ddata['zone']['data'], rtype, name, content)

    def _update_record(self, identifier=None, rtype=None, name=None, content=None):  # pylint: disable=too-many-locals,too-many-branches
        """
        Connects to Hetzner account, changes an existing record and returns a boolean,
        if update was successful or not. Needed identifier or rtype & name to lookup
        over all records of the zone for exactly one record to update.
        """
        with self._session(self.domain, self.domain_id) as ddata:
            # Validate method parameters
            if identifier:
                dtype, dname, dcontent = self._parse_identifier(identifier, ddata['zone']['data'])
                if dtype and dname and dcontent:
                    rtype = rtype if rtype else dtype
                    name = name if name else dname
                    content = content if content else dcontent
                else:
                    LOGGER.warning('Hetzner => Record with identifier \'%s\' does not exist',
                                   identifier)
                    return False

            elif rtype and name and content:
                dtype, dname, dcontent = rtype, name, None
            else:
                LOGGER.warning('Hetzner => Record has no rtype|name|content specified')
                return False

            dname = ddata['cname'] if ddata['cname'] else self._fqdn_name(dname)
            records = self._list_records_in_zone(ddata['zone']['data'], dtype, dname, dcontent)
            if len(records) == 1:
                # Remove record from zone
                rrset = ddata['zone']['data'].get_rdataset(records[0]['name'] + '.',
                                                           rdtype=records[0]['type'])
                rdatas = []
                for rdata in rrset:
                    if self._convert_content(records[0]['type'],
                                             records[0]['content']) != rdata.to_text():
                        rdatas.append(rdata.to_text())
                if rdatas:
                    rdataset = dns.rdataset.from_text_list(rrset.rdclass, rrset.rdtype,
                                                           records[0]['ttl'], rdatas)
                    ddata['zone']['data'].replace_rdataset(records[0]['name'] + '.', rdataset)
                else:
                    ddata['zone']['data'].delete_rdataset(records[0]['name'] + '.',
                                                          records[0]['type'])
                # Add record to zone
                name = ddata['cname'] if ddata['cname'] else self._fqdn_name(name)
                rrset = ddata['zone']['data'].get_rdataset(name, rdtype=rtype, create=True)
                synced_change = False
                for rdata in rrset:
                    if self._convert_content(rtype, content) == rdata.to_text():
                        LOGGER.info('Hetzner => Record with content \'%s\' already exists',
                                    content)
                        synced_change = True
                        break
                if not synced_change:
                    ttl = (rrset.ttl if 0 < rrset.ttl < self._get_lexicon_option('ttl')
                           else self._get_lexicon_option('ttl'))
                    rdataset = dns.rdataset.from_text(rrset.rdclass, rrset.rdtype, ttl,
                                                      self._convert_content(rtype, content))
                    rrset.update(rdataset)
                # Post zone to Hetzner
                synced_change = self._post_zone(ddata['zone'])
                if synced_change:
                    self._propagated_record(rtype, name, self._convert_content(rtype, content),
                                            ddata['nameservers'])
                return synced_change

            LOGGER.warning('Hetzner => Record lookup has not only one match')
            return False

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """
        Connects to Hetzner account, removes an existing record from the zone and returns a
        boolean, if deletion was successful or not. Uses identifier or rtype, name & content to
        lookup over all records of the zone for one or more records to delete.
        """
        with self._session(self.domain, self.domain_id) as ddata:
            # Validate method parameters
            if identifier:
                rtype, name, content = self._parse_identifier(identifier, ddata['zone']['data'])
                if rtype is None or name is None or content is None:
                    LOGGER.info('Hetzner => Record with identifier \'%s\' does not exist',
                                identifier)
                    return True

            name = ddata['cname'] if ddata['cname'] else (self._fqdn_name(name) if name else None)
            records = self._list_records_in_zone(ddata['zone']['data'], rtype, name, content)
            if records:
                # Remove records from zone
                for record in records:
                    rrset = ddata['zone']['data'].get_rdataset(record['name'] + '.',
                                                               rdtype=record['type'])
                    rdatas = []
                    for rdata in rrset:
                        if self._convert_content(record['type'],
                                                 record['content']) != rdata.to_text():
                            rdatas.append(rdata.to_text())
                    if rdatas:
                        rdataset = dns.rdataset.from_text_list(rrset.rdclass, rrset.rdtype,
                                                               record['ttl'], rdatas)
                        ddata['zone']['data'].replace_rdataset(record['name'] + '.', rdataset)
                    else:
                        ddata['zone']['data'].delete_rdataset(record['name'] + '.', record['type'])
                # Post zone to Hetzner
                synced_change = self._post_zone(ddata['zone'])
                return synced_change

            LOGGER.info('Hetzner => Record lookup has no matches')
            return True

    ###############################################################################
    # Provider base helpers
    ###############################################################################

    @staticmethod
    def _create_identifier(rdtype, name, content):
        """
        Creates hashed identifier based on full qualified record type, name & content
        and returns hash.
        """
        sha256 = hashlib.sha256()
        sha256.update((rdtype + '/').encode('UTF-8'))
        sha256.update((name + '/').encode('UTF-8'))
        sha256.update(content.encode('UTF-8'))
        return sha256.hexdigest()[0:7]

    def _parse_identifier(self, identifier, zone=None):
        """
        Parses the record identifier and returns type, name & content of the associated record
        as tuple. The tuple is empty if no associated record found.
        """
        rdtype, name, content = None, None, None
        if len(identifier) > 7:
            parts = identifier.split('/')
            rdtype, name, content = parts[0], parts[1], '/'.join(parts[2:])
        else:
            records = self._list_records_in_zone(zone)
            for record in records:
                if record['id'] == identifier:
                    rdtype, name, content = record['type'], record['name'] + '.', record['content']
        return rdtype, name, content

    def _convert_content(self, rdtype, content):
        """
        Converts type dependent record content into well formed and fully qualified
        content for domain zone and returns content.
        """
        if rdtype == 'TXT':
            if content[0] != '"':
                content = '"' + content
            if content[-1] != '"':
                content += '"'
        if rdtype in ('CNAME', 'MX', 'NS', 'SRV'):
            if content[-1] != '.':
                content = self._fqdn_name(content)
        return content

    def _list_records_in_zone(self, zone, rdtype=None, name=None, content=None):
        """
        Iterates over all records of the zone and returns a list of records filtered
        by record type, name and content. The list is empty if no records found.
        """
        records = []
        rrsets = zone.iterate_rdatasets() if zone else []
        for rname, rdataset in rrsets:
            rtype = dns.rdatatype.to_text(rdataset.rdtype)
            if ((not rdtype or rdtype == rtype)
                    and (not name or name == rname.to_text())):
                for rdata in rdataset:
                    rdata = rdata.to_text()
                    if not content or self._convert_content(rtype, content) == rdata:
                        raw_rdata = self._clean_TXT_record({'type': rtype,
                                                            'content': rdata})['content']
                        data = {
                            'type': rtype,
                            'name': rname.to_text(True),
                            'ttl': int(rdataset.ttl),
                            'content': raw_rdata,
                            'id': Provider._create_identifier(rtype, rname.to_text(), raw_rdata)
                        }
                        records.append(data)
        return records

    def _request(self, action='GET', url='/', data=None, query_params=None):
        """
        Requests to Hetzner by current session and returns the response.
        """
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = self.session.request(action, self.api[self.account]['endpoint'] + url,
                                        params=query_params, data=data)
        response.raise_for_status()
        return response

    ###############################################################################
    # Provider option helpers
    ###############################################################################

    @staticmethod
    def _dns_lookup(name, rdtype, nameservers=None):
        """
        Looks on specified or default system domain nameservers to resolve record type
        & name and returns record set. The record set is empty if no propagated
        record found.
        """
        rrset = dns.rrset.from_text(name, 0, 1, rdtype)
        try:
            resolver = dns.resolver.Resolver()
            resolver.lifetime = 1
            if nameservers:
                resolver.nameservers = nameservers
            rrset = resolver.query(name, rdtype)
            for rdata in rrset:
                LOGGER.debug('DNS Lookup => %s %s %s %s',
                             rrset.name.to_text(), dns.rdataclass.to_text(rrset.rdclass),
                             dns.rdatatype.to_text(rrset.rdtype), rdata.to_text())
        except dns.exception.DNSException as error:
            LOGGER.debug('DNS Lookup => %s', error)
        return rrset

    @staticmethod
    def _get_nameservers(domain):
        """
        Looks for domain nameservers and returns the IPs of the nameservers as a list.
        The list is empty, if no nameservers were found. Needed associated domain zone
        name for lookup.
        """
        nameservers = []
        rdtypes_ns = ['SOA', 'NS']
        rdtypes_ip = ['A', 'AAAA']
        for rdtype_ns in rdtypes_ns:
            for rdata_ns in Provider._dns_lookup(domain, rdtype_ns):
                for rdtype_ip in rdtypes_ip:
                    for rdata_ip in Provider._dns_lookup(rdata_ns.to_text().split(' ')[0],
                                                         rdtype_ip):
                        if rdata_ip.to_text() not in nameservers:
                            nameservers.append(rdata_ip.to_text())
        LOGGER.debug('DNS Lookup => %s IN NS %s', domain, ' '.join(nameservers))
        return nameservers

    @staticmethod
    def _get_dns_cname(name, link=False):
        """
        Looks for associated domain zone, nameservers and linked record name until no
        more linked record name was found for the given fully qualified record name or
        the CNAME lookup was disabled, and then returns the parameters as a tuple.
        """
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 1
        domain = dns.resolver.zone_for_name(name, resolver=resolver).to_text(True)
        nameservers = Provider._get_nameservers(domain)
        cname = None
        links, max_links = 0, 5
        while link:
            if links >= max_links:
                LOGGER.error('Hetzner => Record %s has more than %d linked CNAME '
                             'records. Reduce the amount of CNAME links!',
                             name, max_links)
                raise AssertionError
            qname = cname if cname else name
            rrset = Provider._dns_lookup(qname, 'CNAME', nameservers)
            if rrset:
                links += 1
                cname = rrset[0].to_text()
                qdomain = dns.resolver.zone_for_name(cname, resolver=resolver).to_text(True)
                if domain != qdomain:
                    domain = qdomain
                    nameservers = Provider._get_nameservers(qdomain)
            else:
                link = False
        if cname:
            LOGGER.info('Hetzner => Record %s has CNAME %s', name, cname)
        return domain, nameservers, cname

    def _link_record(self):
        """
        Checks restrictions for use of CNAME lookup and returns a tuple of the
        fully qualified record name to lookup and a boolean, if a CNAME lookup
        should be done or not. The fully qualified record name is empty if no
        record name is specified by this provider.
        """
        action = self._get_lexicon_option('action')
        identifier = self._get_lexicon_option('identifier')
        rdtype = self._get_lexicon_option('type')
        name = (self._fqdn_name(self._get_lexicon_option('name'))
                if self._get_lexicon_option('name') else None)
        link = self._get_provider_option('linked')
        qname = name
        if identifier:
            rdtype, name, _ = self._parse_identifier(identifier)
        if action != 'list' and rdtype in ('A', 'AAAA', 'TXT') and name and link == 'yes':
            if action != 'update' or name == qname or not qname:
                LOGGER.info('Hetzner => Enable CNAME lookup '
                            '(see --linked parameter)')
                return name, True
        LOGGER.info('Hetzner => Disable CNAME lookup '
                    '(see --linked parameter)')
        return name, False

    def _propagated_record(self, rdtype, name, content, nameservers=None):
        """
        If the publicly propagation check should be done, waits until the domain nameservers
        responses with the propagated record type, name & content and returns a boolean,
        if the publicly propagation was successful or not.
        """
        latency = self._get_provider_option('latency')
        propagated = self._get_provider_option('propagated')
        if propagated == 'yes':
            retry, max_retry = 0, 20
            while retry < max_retry:
                for rdata in Provider._dns_lookup(name, rdtype, nameservers):
                    if content == rdata.to_text():
                        LOGGER.info('Hetzner => Record %s has %s %s', name, rdtype, content)
                        return True
                retry += 1
                retry_log = (', retry ({}/{}) in {}s...'.format((retry + 1), max_retry, latency)
                             if retry < max_retry else '')
                LOGGER.info('Hetzner => Record is not propagated%s', retry_log)
                time.sleep(latency)
        return False

    ###############################################################################
    # Hetzner API helpers
    ###############################################################################

    @staticmethod
    def _filter_dom(dom, filters, last_find_all=False):
        """
        If not exists, creates an DOM from a given session response, then filters the DOM
        via given API filters and returns the filtered DOM. The DOM is empty if the filters
        have no match.
        """
        if isinstance(dom, string_types):
            dom = BeautifulSoup(dom, 'html.parser')
        for idx, find in enumerate(filters, start=1):
            if not dom:
                break
            name, attrs = find.get('name'), find.get('attrs', {})
            if len(filters) == idx and last_find_all:
                dom = dom.find_all(name, attrs=attrs) if name else dom.find_all(attrs=attrs)
            else:
                dom = dom.find(name, attrs=attrs) if name else dom.find(attrs=attrs)
        return dom

    @staticmethod
    def _extract_hidden_data(dom):
        """
        Extracts hidden input data from DOM and returns the data as dictionary.
        """
        input_tags = dom.find_all('input', attrs={'type': 'hidden'})
        data = {}
        for input_tag in input_tags:
            data[input_tag['name']] = input_tag['value']
        return data

    @staticmethod
    def _extract_domain_id(string, regex):
        """
        Extracts domain ID from given string and returns the domain ID.
        """
        regex = re.compile(regex)
        match = regex.search(string)
        if not match:
            return False
        return str(match.group(1))

    @contextmanager
    def _session(self, domain, domain_id=None, get_zone=True):
        """
        Generates, authenticates and exits session to Hetzner account, and
        provides tuple of additional needed domain data (domain nameservers,
        zone and linked record name) to public methods. The tuple parameters
        are empty if not existent or specified. Exits session and raises error
        if provider fails during session.
        """
        name, link = self._link_record()
        qdomain, nameservers, cname = Provider._get_dns_cname(
            (name if name else domain + '.'), link)
        qdomain_id, zone = domain_id, None
        self.session = self._auth_session(self.username, self.password)
        try:
            if not domain_id or qdomain != domain:
                qdomain_id = self._get_domain_id(qdomain)
            if qdomain == domain:
                self.domain_id = qdomain_id
            if get_zone:
                zone = self._get_zone(qdomain, qdomain_id)
            yield {'nameservers': nameservers, 'zone': zone, 'cname': cname}
        except Exception as exc:
            raise exc
        finally:
            self._exit_session()

    def _auth_session(self, username, password):
        """
        Creates session to Hetzner account, authenticates with given credentials and
        returns the session, if authentication was successful. Otherwise raises error.
        """
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

    def _exit_session(self):
        """
        Exits session to Hetzner account and returns.
        """
        api = self.api[self.account]
        response = self._get(api['exit']['GET']['url'])
        if not Provider._filter_dom(response.text, api['filter']):
            LOGGER.info('Hetzner => Exit session')
        else:
            LOGGER.warning('Hetzner => Unable to exit session')
        self.session = None
        return True

    def _get_domain_id(self, domain):
        """
        Pulls all domains managed by authenticated Hetzner account, extracts their IDs
        and returns the ID for the current domain, if exists. Otherwise raises error.
        """
        api = self.api[self.account]['domain_id']
        qdomain = dns.name.from_text(domain).to_unicode(True)
        domains, last_count, page = {}, -1, 0
        while last_count != len(domains):
            last_count = len(domains)
            page += 1
            url = (api['GET'].copy()).get('url', '/').replace('<index>', str(page))
            params = api['GET'].get('params', {}).copy()
            for param in params:
                params[param] = params[param].replace('<index>', str(page))
            response = self._get(url, query_params=params)
            domain_tags = Provider._filter_dom(response.text, api['filter'], True)
            for domain_tag in domain_tags:
                domain_id = Provider._extract_domain_id(dict(domain_tag.attrs)[api['id']['attr']],
                                                        api['id']['regex'])
                domain = (Provider._filter_dom(domain_tag, api['domain'])
                          .renderContents().decode('UTF-8'))
                domains[domain] = domain_id
                if domain == qdomain:
                    LOGGER.info('Hetzner => Get ID %s for domain %s', domain_id, qdomain)
                    return domain_id
        LOGGER.error('Hetzner => ID for domain %s does not exists', qdomain)
        raise AssertionError

    def _get_zone(self, domain, domain_id):
        """
        Pulls the zone for the current domain from authenticated Hetzner account and
        returns it as an zone object.
        """
        api = self.api[self.account]
        for request in api['zone']['GET']:
            url = (request.copy()).get('url', '/').replace('<id>', domain_id)
            params = request.get('params', {}).copy()
            for param in params:
                params[param] = params[param].replace('<id>', domain_id)
            response = self._get(url, query_params=params)
        dom = Provider._filter_dom(response.text, api['filter'])
        zone_file_filter = [{'name': 'textarea', 'attrs': {'name': api['zone']['file']}}]
        zone_file = Provider._filter_dom(dom, zone_file_filter).renderContents().decode('UTF-8')
        hidden = Provider._extract_hidden_data(dom)
        zone = {'data': dns.zone.from_text(zone_file, origin=domain, relativize=False),
                'hidden': hidden}
        LOGGER.info('Hetzner => Get zone for domain %s', domain)
        return zone

    def _post_zone(self, zone):
        """
        Pushes updated zone for current domain to authenticated Hetzner account and
        returns a boolean, if update was successful or not. Furthermore, waits until
        the zone has been taken over, if it is a Hetzner Robot account.
        """
        api = self.api[self.account]['zone']
        data = zone['hidden']
        data[api['file']] = zone['data'].to_text(relativize=True)
        response = self._post(api['POST']['url'], data=data)
        if Provider._filter_dom(response.text, api['filter']):
            LOGGER.error('Hetzner => Unable to update zone for domain %s: Syntax error\n\n%s',
                         zone['data'].origin.to_unicode(True),
                         zone['data'].to_text(relativize=True).decode('UTF-8'))
            return False

        LOGGER.info('Hetzner => Update zone for domain %s',
                    zone['data'].origin.to_unicode(True))
        if self.account == 'robot':
            latency = self._get_provider_option('latency')
            LOGGER.info('Hetzner => Wait %ds until Hetzner Robot has taken over zone...',
                        latency)
            time.sleep(latency)
        return True
