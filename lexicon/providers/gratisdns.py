"""Module provider for GratisDNS"""
from __future__ import absolute_import

import logging
import requests
# Due to optional requirement
try:
    from bs4 import BeautifulSoup
except ImportError:
    pass

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['gratisdns.dk']


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument(
        "--auth-username", help="specify email address for authentication")
    subparser.add_argument(
        "--auth-password", help="specify password for authentication")


class Provider(BaseProvider):
    """Provider class for GratisDNS"""
    # XXX: Identifiers change on updates

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://admin.gratisdns.com'
        self.cookies = {}

    def _authenticate(self):
        # Getting required cookie "ORGID"
        payload = {"action": "logmein",
                   "login": self._get_provider_option('auth_username'),
                   "password": self._get_provider_option('auth_password')}
        # Cannot allow redirects, as we miss the cookie then
        response = requests.post(self.api_endpoint,
                                 data=payload,
                                 allow_redirects=False)
        response.raise_for_status()

        if "ORGID" not in response.cookies:
            raise Exception("Unexpected auth response")
        self.cookies["ORGID"] = response.cookies["ORGID"]

        # Make sure domain exists
        # domain is stored in self.domain from BaseProvider
        domains = self._list_domains()
        for domain in domains:
            if domain == self.domain:
                # Domain name is the ID
                self.domain_id = domain

        if self.domain_id is None:
            raise Exception('Domain {} not found'.format(self.domain))

    def _list_domains(self):
        query_params = {'action': 'dns_primarydns'}
        response = self._get(query_params=query_params)
        html = BeautifulSoup(response.content, "html.parser")
        # NOTE: This could be more robust, by checking more of the tree
        domains = [x.contents[0] for x in html.find_all("th", scope="row")]
        LOGGER.debug('list_domains: %s', domains)

        return domains

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    # pylint: disable=too-many-locals
    def _list_records(self, rtype=None, name=None, content=None):
        query_params = {'action': 'dns_primary_changeDNSsetup',
                        'user_domain': self.domain_id}
        response = self._get(query_params=query_params)
        html = BeautifulSoup(response.content, "html.parser")
        # List of records
        all_records = []
        # DNS records are grouped by type
        dns_record_types = html.find_all("div", 'dns-records')
        for dns_record in dns_record_types:
            # Find the title of this group, aka record type
            record_type = dns_record.find("h2").contents[0].strip()
            # The entries themselves follow in the table below
            # Each row is a single entry
            entry_table_rows = dns_record.find('tbody').find_all('tr')
            for row in entry_table_rows:
                cols = row.find_all('td')
                # Format is; name, content, ttl, EDIT/DELETE button
                record_name = cols[0].contents[0]
                record_content = cols[1].contents[0]
                record_ttl = cols[2].contents[0]
                # We have to pull the ID from the button link
                record_id = None
                button_link = cols[3].find('a')
                if button_link:
                    start = button_link['href'].index('&id=')+4
                    end = button_link['href'].index('&', start)
                    record_id = button_link['href'][start:end]

                processed_record = {
                    'type': record_type,
                    'name': record_name,
                    'ttl': record_ttl,
                    'content': record_content,
                    'id': record_id,
                }
                all_records.append(processed_record)

        records = self._filter_records(
            records=all_records,
            rtype=rtype,
            name=name,
            content=content
        )
        LOGGER.debug('list_records: %s', records)
        return records

    # Filter a list of records based on criteria
    # NOTE: Duplicate of lexicon/providers/transip.py _filter_records
    def _filter_records(self, records, rtype=None, name=None, content=None):
        _records = []
        for record in records:
            if ((not rtype or record['type'] == rtype) and  # pylint: disable=too-many-boolean-expressions
                    (not name or self._full_name(record['name']) == self._full_name(name)) and
                    (not content or record['content'] == content)):
                _records.append(record)
        return _records

    # pylint: disable=no-self-use
    def _get_content_entry(self, rtype):
        if rtype == 'TXT':
            return 'txtdata'
        if rtype == 'A':
            return 'ip'
        if rtype == 'AAAA':
            return 'ip'
        if rtype == 'CNAME':
            return 'cname'
        LOGGER.error('unknown record type')
        return None

    # Create record. If record already exists with the same content, do nothing
    def _create_record(self, rtype, name, content):
        # Figure out TTL
        ttl = 43200
        if self._get_lexicon_option('ttl'):
            ttl = self._get_lexicon_option('ttl')

        content_entry = self._get_content_entry(rtype)
        if content_entry is None:
            return False

        # Prepare query params and payload
        query_params = {'action': 'dns_primary_record_add_' + rtype.lower(),
                        'user_domain': self.domain_id}
        payload = {'action': 'dns_primary_record_added_' + rtype.lower(),
                   'name': self._full_name(name),
                   'ttl': ttl,
                   content_entry: content,
                   'user_domain': self.domain_id}
        self._post(query_params=query_params, data=payload)
        # response = self._post(query_params=query_params, data=payload)
        # NOTE: We shouldn't return False on duplicate?
        #       The specification seems a little wage on this.
        # html = BeautifulSoup(response.content, "html.parser")
        # error = html.find('td', 'table-danger')
        # success = (error is None)

        LOGGER.debug('create_record: %s', True)
        return True

    def _lookup_record(self, identifier):
        # Pull all the records we know
        records = self._list_records()
        # Find the one with the provided identifier
        record = next((x for x in records if x['id'] == identifier), None)
        return record

    # Create or update a record.
    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        record = None
        # Try to find, either by identifier or by searching
        if identifier:
            # Find the relevant record by id
            record = self._lookup_record(identifier)
        else:
            # Find the relevant record by rtype and name
            records = self._list_records(rtype=rtype, name=name)
            if len(records) == 1:
                record = records[0]
                identifier = record['id']
        # If none is found, create it
        if record is None:
            return self._create_record(rtype, name, content)

        # Update ttl if provided
        if self._get_lexicon_option('ttl'):
            record['ttl'] = self._get_lexicon_option('ttl')
        # Update name if provided
        if name:
            record['name'] = self._full_name(name)
        if content:
            record['content'] = content

        content_entry = self._get_content_entry(rtype)
        if content_entry is None:
            return False

        # Prepare query params and payload
        query_params = {'action': 'dns_primary_record_edit_' + rtype.lower(),
                        'user_domain': self.domain_id,
                        'id': identifier}
        payload = {'action': 'dns_primary_record_update_' + rtype.lower(),
                   'id': identifier,
                   'name': record['name'],
                   'ttl': record['ttl'],
                   content_entry: record['content'],
                   'user_domain': self.domain_id}
        response = self._post(query_params=query_params, data=payload)
        html = BeautifulSoup(response.content, "html.parser")
        error = html.find('td', 'table-danger')
        success = (error is None)

        LOGGER.debug('update_record: %s', success)
        return success

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_record_id)

        success = True
        for record_id in delete_record_id:
            # Lookup the record to determine rtype
            if rtype is None:
                record = self._lookup_record(record_id)
                rtype = record['type']

            # Prepare query params and payload
            query_params = {'action': 'dns_primary_delete_' + rtype.lower(),
                            'user_domain': self.domain_id,
                            'id': record_id}
            # _get is intentional, get really is used for deletion on gratisdns
            response = self._get(query_params=query_params)
            html = BeautifulSoup(response.content, "html.parser")
            error = html.find('td', 'table-danger')
            success = success and (error is None)

        LOGGER.debug('delete_record: %s', success)
        return success

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = requests.request(action, self.api_endpoint + url,
                                    params=query_params,
                                    data=data,
                                    cookies=self.cookies)

        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response
