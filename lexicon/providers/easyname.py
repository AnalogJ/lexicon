"""Module provider for Easyname DNS"""
from __future__ import absolute_import, print_function
import logging

from requests import Response, Session

# Handling optional dependency for this provider
try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    pass

from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['easyname.eu']


def provider_parser(subparser):
    """Configure provider parser for Easyname DNS"""
    subparser.description = """A provider for Easyname DNS."""
    subparser.add_argument(
        '--auth-username',
        help='Specify username used to authenticate'
    )
    subparser.add_argument(
        '--auth-password',
        help='Specify password used to authenticate',
    )


class Provider(BaseProvider):
    """
        easyname provider
    """

    URLS = {
        'login': 'https://my.easyname.com/en/login',
        'domain_list': 'https://my.easyname.com/domains/',
        'overview': 'https://my.easyname.com/hosting/view-user.php',
        'dns': 'https://my.easyname.com/domains/settings/dns.php?domain={}',
        'dns_create_entry': 'https://my.easyname.com/domains/settings/form.php?domain={}',
        'dns_delete_entry':
            'https://my.easyname.com/domains/settings/delete_record.php?domain={}&confirm=1&id={}'
    }

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.session = Session()
        self.domain_id = None
        self._records = None

    def _authenticate(self):
        """
        Authenticates against Easyname website and try to find out the domain
        id.
        Easyname uses a CSRF token in its login form, so two requests are
        neccessary to actually login.

        Returns:
          bool: True if domain id was found.

        Raises:
          AssertionError: When a request returns unexpected or unknown data.
          ValueError: When login data is wrong or the domain does not exist.
        """
        csrf_token = self._get_csrf_token()
        self._login(csrf_token)

        domain_text_element = self._get_domain_text_of_authoritative_zone()
        self.domain_id = self._get_domain_id(domain_text_element)
        LOGGER.debug('Easyname domain ID: %s', self.domain_id)

        return True

    def _create_record(self, rtype, name, content):
        return self._create_record_internal(rtype=rtype, name=name, content=content)

    def _create_record_internal(self, rtype, name, content, identifier=None):
        """
        Create a new DNS entry in the domain zone if it does not already exist.

        Args:
          rtype (str): The DNS type (e.g. A, TXT, MX, etc) of the new entry.
          name (str): The name of the new DNS entry, e.g the domain for which a
                      MX entry shall be valid.
          content (str): The content of the new DNS entry, e.g. the mail server
                         hostname for a MX entry.
          [identifier] (str): The easyname id of a DNS entry. Use to overwrite an
                    existing entry.

        Returns:
          bool: True if the record was created successfully, False otherwise.
        """
        name = self._relative_name(name) if name is not None else name
        LOGGER.debug('Creating record with name %s', name)
        if self._is_duplicate_record(rtype, name, content):
            return True

        data = self._get_post_data_to_create_dns_entry(rtype, name, content, identifier)
        LOGGER.debug('Create DNS data: %s', data)
        create_response = self.session.post(
            self.URLS['dns_create_entry'].format(self.domain_id),
            data=data
        )
        self._invalidate_records_cache()
        self._log('Create DNS entry', create_response)

        # Pull a list of records and check for ours
        was_success = len(self._list_records(rtype, name, content)) > 0
        if was_success:
            msg = 'Successfully added record %s'
        else:
            msg = 'Failed to add record %s'

        LOGGER.info(msg, name)
        return was_success

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """
        Delete one or more DNS entries in the domain zone that match the given
        criteria.

        Args:
          [identifier] (str): An ID to match against DNS entry easyname IDs.
          [rtype] (str): A DNS rtype (e.g. A, TXT, MX, etc) to match against DNS
                      entry types.
          [name] (str): A name to match against DNS entry names.
          [content] (str): A content to match against a DNS entry contents.

        Returns:
          bool: True if the record(s) were deleted successfully, False
                otherwise.
        """
        success_url = self.URLS['dns'].format(self.domain_id)
        record_ids = self._get_matching_dns_entry_ids(identifier, rtype,
                                                      name, content)
        LOGGER.debug('Record IDs to delete: %s', record_ids)

        success = True
        for rec_id in record_ids:
            delete_response = self.session.get(
                self.URLS['dns_delete_entry'].format(self.domain_id, rec_id))
            self._invalidate_records_cache()
            self._log('Delete DNS entry {}'.format(rec_id), delete_response)
            success = success and delete_response.url == success_url

        return success

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        """
        Update a DNS entry identified by identifier or name in the domain zone.
        Any non given argument will leave the current value of the DNS entry.

        Args:
          identifier (str): The easyname id of the DNS entry to update.
          [rtype] (str): The DNS rtype (e.g. A, TXT, MX, etc) of the new entry.
          [name] (str): The name of the new DNS entry, e.g the domain for which
                        a MX entry shall be valid.
          [content] (str): The content of the new DNS entry, e.g. the mail
                           server hostname for a MX entry.

        Returns:
          bool: True if the record was updated successfully, False otherwise.

        Raises:
          AssertionError: When a request returns unexpected or unknown data.
        """
        if identifier is not None:
            identifier = int(identifier)
            records = self._list_records_internal(identifier=identifier)
        else:
            records = self._list_records_internal(name=name, rtype=rtype)
        LOGGER.debug('Records to update (%d): %s', len(records), records)
        assert records, 'No record found to update'
        success = True

        for record in records:
            name = name if name is not None else record['name']
            rtype = rtype if rtype is not None else record['type']
            content = content if content is not None \
                else record['content']
            success = success and self._create_record_internal(
                rtype, name, content, record['id'])
        return success

    def _list_records(self, rtype=None, name=None, content=None):
        return self._list_records_internal(rtype=rtype, name=name, content=content)

    def _list_records_internal(self, rtype=None, name=None, content=None, identifier=None):
        """
        Filter and list DNS entries of domain zone on Easyname.
        Easyname shows each entry in a HTML table row and each attribute on a
        table column.

        Args:
          [rtype] (str): Filter by DNS rtype (e.g. A, TXT, MX, etc)
          [name] (str): Filter by the name of the DNS entry, e.g the domain for
                      which a MX entry shall be valid.
          [content] (str): Filter by the content of the DNS entry, e.g. the
                           mail server hostname for a MX entry.
          [identifier] (str): Filter by the easyname id of the DNS entry.

        Returns:
          list: A list of DNS entries. A DNS entry is an object with DNS
                attribute names as keys (e.g. name, content, priority, etc)
                and additionally an id.

        Raises:
          AssertionError: When a request returns unexpected or unknown data.
        """
        name = self._full_name(name) if name is not None else name
        if self._records is None:
            records = []
            rows = self._get_dns_entry_trs()

            for index, row in enumerate(rows):
                self._log('DNS list entry', row)
                try:
                    rec = {}
                    if row.has_attr('ondblclick'):
                        rec['id'] = int(row['ondblclick'].split(
                            'id=')[1].split("'")[0])
                    else:
                        rec['id'] = -index

                    columns = row.find_all('td')
                    rec['name'] = (columns[0].string or '').strip()
                    rec['type'] = (columns[1].contents[1] or '').strip()
                    rec['content'] = (columns[2].string or '').strip()
                    rec['priority'] = (columns[3].string or '').strip()
                    rec['ttl'] = (columns[4].string or '').strip()

                    if rec['priority']:
                        rec['priority'] = int(rec['priority'])

                    if rec['ttl']:
                        rec['ttl'] = int(rec['ttl'])
                except Exception as error:
                    errmsg = 'Cannot parse DNS entry ({}).'.format(error)
                    LOGGER.warning(errmsg)
                    raise AssertionError(errmsg)
                records.append(rec)
            self._records = records

        records = self._filter_records(self._records, rtype, name, content, identifier)
        LOGGER.debug('Final records (%d): %s', len(records), records)
        return records

    def _request(self, action='GET', url='/', data=None, query_params=None):
        pass

    def _invalidate_records_cache(self):
        """
        Invalidate DNS entries cache such that list_records will do a new
        request to retrieve DNS entries.
        """
        self._records = None

    def _get_post_data_to_create_dns_entry(self, rtype, name, content, identifier=None):
        """
        Build and return the post date that is needed to create a DNS entry.
        """
        is_update = identifier is not None
        record = None
        if is_update:
            records = self._list_records_internal(identifier=identifier)
            assert len(records) == 1, 'ID is not unique or does not exist'
            record = records[0]
            LOGGER.debug('Create post data to update record: %s', record)

        data = {
            'id': str(identifier) if is_update else '',
            'action': 'save',
            'name': name,
            'type': rtype,
            'content': content,
            'prio': str(record['priority']) if is_update else '10',
            'ttl': str(record['ttl']) if is_update else '360',
            'commit': ''
        }
        ttl = self._get_lexicon_option('ttl')
        if ttl and ttl > 360:
            data['ttl'] = str(ttl)

        prio = self._get_lexicon_option('priority')
        if prio and prio > 0:
            data['prio'] = str(prio)

        return data

    def _is_duplicate_record(self, rtype, name, content):
        """Check if DNS entry already exists."""
        records = self._list_records(rtype, name, content)
        is_duplicate = len(records) >= 1
        if is_duplicate:
            LOGGER.info('Duplicate record %s %s %s, NOOP', rtype, name, content)
        return is_duplicate

    def _get_matching_dns_entry_ids(self, identifier=None, rtype=None,
                                    name=None, content=None):
        """Return a list of DNS entries that match the given criteria."""
        record_ids = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            record_ids = [record['id'] for record in records]
        else:
            record_ids.append(identifier)
        return record_ids

    def _get_dns_entry_trs(self):
        """
        Return the TR elements holding the DNS entries.
        """
        dns_list_response = self.session.get(
            self.URLS['dns'].format(self.domain_id))
        self._log('DNS list', dns_list_response)
        assert dns_list_response.status_code == 200, \
            'Could not load DNS entries.'

        html = BeautifulSoup(dns_list_response.content, 'html.parser')
        self._log('DNS list', html)
        dns_table = html.find('table', {'id': 'cp_domains_dnseintraege'})
        assert dns_table is not None, 'Could not find DNS entry table'

        def _is_zone_tr(elm):
            has_ondblclick = elm.has_attr('ondblclick')
            has_class = elm.has_attr('class')
            return elm.name.lower() == 'tr' and (has_class or has_ondblclick)

        rows = dns_table.findAll(_is_zone_tr)
        assert rows is not None and rows, 'Could not find any DNS entries'
        return rows

    def _filter_records(self, records, rtype=None, name=None, content=None, identifier=None):  # pylint: disable=too-many-arguments,no-self-use
        """
        Filter dns entries based on type, name or content.
        """
        if not records:
            return []
        if identifier is not None:
            LOGGER.debug('Filtering %d records by id: %s', len(records), identifier)
            records = [record for record in records if record['id'] == identifier]
        if rtype is not None:
            LOGGER.debug('Filtering %d records by type: %s', len(records), rtype)
            records = [record for record in records if record['type'] == rtype]
        if name is not None:
            LOGGER.debug('Filtering %d records by name: %s', len(records), name)
            if name.endswith('.'):
                name = name[:-1]
            records = [record for record in records if name == record['name']]
        if content is not None:
            LOGGER.debug('Filtering %d records by content: %s', len(records), content.lower())
            records = [record for record in records if
                       record['content'].lower() == content.lower()]
        return records

    def _get_csrf_token(self):
        """Return the CSRF Token of easyname login form."""
        home_response = self.session.get(self.URLS['login'])
        self._log('Home', home_response)
        assert home_response.status_code == 200, \
            'Could not load Easyname login page.'

        html = BeautifulSoup(home_response.content, 'html.parser')
        self._log('Home', html)
        csrf_token_field = html.find('input', {'id': 'loginxtoken'})
        assert csrf_token_field is not None, 'Could not find login token.'
        return csrf_token_field['value']

    def _login(self, csrf_token):
        """Attempt to login session on easyname."""
        login_response = self.session.post(
            self.URLS['login'],
            data={
                'username': self._get_provider_option('auth_username') or '',
                'password': self._get_provider_option('auth_password') or '',
                'submit': '',
                'loginxtoken': csrf_token,
            }
        )
        self._log('Login', login_response)
        assert login_response.status_code == 200, \
            'Could not login due to a network error.'
        assert login_response.url == self.URLS['domain_list'], \
            'Easyname login failed, bad EASYNAME_USER or EASYNAME_PASS.%s' % login_response.url

    def _get_domain_text_of_authoritative_zone(self):
        """Get the authoritative name zone."""
        # We are logged in, so get the domain list
        zones_response = self.session.get(self.URLS['domain_list'])
        self._log('Zone', zones_response)
        assert zones_response.status_code == 200, \
            'Could not retrieve domain list due to a network error.'

        html = BeautifulSoup(zones_response.content, 'html.parser')
        self._log('Zone', html)
        domain_table = html.find('table', {'id': 'cp_domain_table'})
        assert domain_table is not None, 'Could not find domain table'

        # (Sub)domains can either be managed in their own zones or by the
        # zones of their parent (sub)domains. Iterate over all subdomains
        # (starting with the deepest one) and see if there is an own zone
        # for it.
        domain = self.domain or ''
        domain_text = None
        subdomains = domain.split('.')
        while True:
            domain = '.'.join(subdomains)
            LOGGER.debug('Check if %s has own zone', domain)
            domain_text = domain_table.find(string=domain)
            if domain_text is not None or len(subdomains) < 3:
                break
            subdomains.pop(0)

        # Update domain to equal the zone's domain. This is important if we are
        # handling a subdomain that has no zone of itself. If we do not do
        # this, self._relative_name will strip also a part of the subdomain
        # away.
        self.domain = domain
        assert domain_text is not None, \
            'The domain does not exist on Easyname.'
        return domain_text

    def _get_domain_id(self, domain_text_element):  # pylint: disable=no-self-use
        """Return the easyname id of the domain."""
        try:
            # Hierarchy: TR > TD > SPAN > Domain Text
            tr_anchor = domain_text_element.parent.parent.parent
            td_anchor = tr_anchor.find('td', {'class': 'td_2'})
            link = td_anchor.find('a')['href']
            domain_id = link.rsplit('/', 1)[-1]
            return domain_id
        except Exception as error:
            errmsg = ('Cannot get the domain id even though the domain seems '
                      'to exist (%s).', error)
            LOGGER.warning(errmsg)
            raise AssertionError(errmsg)

    def _log(self, name, element):  # pylint: disable=no-self-use
        """
        Log Response and Tag elements. Do nothing if elements is none of them.
        """
        if isinstance(element, Response):
            LOGGER.debug('%s response: URL=%s Code=%s', name, element.url, element.status_code)
        elif isinstance(element, (BeautifulSoup, Tag)):
            LOGGER.debug('%s HTML:\n%s', name, element)
