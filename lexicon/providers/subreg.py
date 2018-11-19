"""Provide support to Lexicon for Subreg.cz DNS changes."""

from __future__ import absolute_import
import collections
import logging

from lexicon.providers.base import Provider as BaseProvider


try:
    import zeep  # Optional dependency
except:
    pass

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['subreg.cz']


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-username", help="specify username for authentication")
    subparser.add_argument(
        "--auth-password", help="specify password for authentication")


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.ssid = None

        client = zeep.Client("https://subreg.cz/wsdl")
        self.api = client.service

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider, so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason, of if the domain does not exist.
    def authenticate(self):
        """Logs-in the user and checks the domain name"""
        if not self._get_provider_option('auth_username') or not self._get_provider_option('auth_password'):
            raise Exception(
                'No valid authentication data passed, expected: auth-username and auth-password')
        response = self._request_login(self._get_provider_option('auth_username'),
                                       self._get_provider_option('auth_password'))
        if 'ssid' in response:
            self.ssid = response['ssid']
            domains = self.domains_list()
            if any((domain['name'] == self.domain for domain in domains)):
                self.domain_id = self.domain
            else:
                raise Exception("Unknown domain {}".format(self.domain))
        else:
            raise Exception("No SSID provided by server")

    # Create record. If record already exists with the same content, do nothing.
    def create_record(self, type, name, content):
        """Creates a new unique record"""
        found = self.list_records(type, name, content)
        if len(found) > 0:
            return True

        record = self._create_request_record(None, type, name, content,
                                             self._get_lexicon_option('ttl'),
                                             self._get_lexicon_option('priority'))

        self._request_add_dns_record(record)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        """Lists all records by the type, name and content"""
        return self._list_records(identifier=None, type=type, name=name, content=content)

    # Update a record. Identifier must be specified.
    def update_record(self, identifier, type=None, name=None, content=None):
        """Updates a record. Name changes are allowed, but the record identifier will change"""
        if identifier is not None:
            if name is not None:
                records = self._list_records(identifier=identifier)
                if len(records) == 1 and records[0]['name'] != self._full_name(name):
                    # API does not allow us to update name directly
                    self._update_record_with_name(
                        records[0], type, name, content)
                else:
                    self._update_record(identifier, type, content)
            else:
                self._update_record(identifier, type, content)
        else:
            guessed_record = self._guess_record(type, name)
            self._update_record(guessed_record['id'], type, content)
        return True

    def _update_record(self, identifier, type, content):
        """Updates existing record with no sub-domain name changes"""
        record = self._create_request_record(identifier, type, None, content,
                                             self._get_lexicon_option('ttl'),
                                             self._get_lexicon_option('priority'))

        self._request_modify_dns_record(record)

    def _update_record_with_name(self, old_record, type, new_name, content):
        """Updates existing record and changes it's sub-domain name"""
        new_type = type if type else old_record['type']

        new_ttl = self._get_lexicon_option('ttl')
        if new_ttl is None and 'ttl' in old_record:
            new_ttl = old_record['ttl']

        new_priority = self._get_lexicon_option('priority')
        if new_priority is None and 'priority' in old_record:
            new_priority = old_record['priority']

        new_content = content
        if new_content is None and 'content' in old_record:
            new_content = old_record['content']

        record = self._create_request_record(None,
                                             new_type,
                                             new_name,
                                             new_content,
                                             new_ttl,
                                             new_priority)

        # This will be a different domain name, so no name collision should
        # happen. First create a new entry and when it succeeds, delete the old
        # one.
        self._request_add_dns_record(record)
        self._request_delete_dns_record_by_id(old_record['id'])

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        """Deletes an existing record"""
        to_delete_ids = list()
        if identifier:
            to_delete_ids.append(identifier)
        else:
            for record in self.list_records(type, name, content):
                to_delete_ids.append(record["id"])

        for to_delete_id in to_delete_ids:
            self._request_delete_dns_record_by_id(to_delete_id)
        return True

    # Get list of registered domains
    def domains_list(self):
        response = self._request_domains_list()
        return response['domains'] if 'domains' in response else list()

    def _create_request_record(self, identifier, type, name, content, ttl, priority):
        """Creates record for Subreg API calls"""
        record = collections.OrderedDict()

        # Mandatory content

        # Just for update - not for creation
        if identifier is not None:
            record['id'] = identifier

        record['type'] = type

        # Just for creation - not for update
        if name is not None:
            record['name'] = self._relative_name(name)

        # Optional content
        if content is not None:
            record['content'] = content
        if ttl is not None:
            record['ttl'] = ttl
        if priority is not None:
            record['prio'] = priority
        return record

    def _create_response_record(self, response):
        """Creates record for lexicon API calls"""
        record = dict()
        record['id'] = response['id']
        record['type'] = response['type']
        record['name'] = self._full_name(response['name'])
        if 'content' in response:
            record['content'] = response['content'] or ""
        if 'ttl' in response:
            record['ttl'] = response['ttl']
        if 'prio' in response:
            record['priority'] = response['prio']
        return record

    def _full_name(self, name):
        """Returns full domain name of a sub-domain name"""
        # Handle None and empty strings
        if not name:
            return self.domain
        else:
            return super(Provider, self)._full_name(name)

    def _relative_name(self, name):
        """Returns sub-domain of a domain name"""
        # Handle None and empty strings as None
        if not name:
            return None
        else:
            subdomain = super(Provider, self)._relative_name(name)
            return subdomain if subdomain else None

    # List all records. Return an empty list if no records found
    # identifier, type, name and content are used to filter records.
    def _list_records(self, identifier=None, type=None, name=None, content=None):
        """Lists all records by the specified criteria"""
        response = self._request_get_dns_zone()
        if 'records' in response:
            # Interpret empty string as None because zeep does so too
            content_check = content if content != "" else None
            name_check = self._relative_name(name)

            # Stringize the identifier to prevent any type differences
            identifier_check = str(
                identifier) if identifier is not None else None

            filtered_records = [record for record in response['records'] if
                                (identifier is None or str(record['id']) == identifier_check) and
                                (type is None or record['type'] == type) and
                                (name is None or record['name'] == name_check) and
                                (content is None or ('content' in record and record['content'] == content_check))]
            records = [self._create_response_record(
                filtered_record) for filtered_record in filtered_records]
        else:
            records = []
        return records

    def _guess_record(self, type, name=None, content=None):
        """Tries to find existing unique record by type, name and content"""
        records = self._list_records(
            identifier=None, type=type, name=name, content=content)
        if len(records) == 1:
            return records[0]
        elif len(records) > 1:
            raise Exception(
                'Identifier was not provided and several existing records match the request for {0}/{1}'.format(type, name))
        else:
            raise Exception(
                'Identifier was not provided and no existing records match the request for {0}/{1}'.format(type, name))

    def _request_login(self, login, password):
        """Sends Login request"""
        return self._request("Login",
                             login=login,
                             password=password)

    def _request_domains_list(self):
        """Sends Domains_List request"""
        return self._request("Domains_List")

    def _request_get_dns_zone(self):
        """Sends Get_DNS_Zone request"""
        return self._request("Get_DNS_Zone",
                             domain=self.domain)

    def _request_add_dns_record(self, record):
        """Sends Add_DNS_Record request"""
        return self._request("Add_DNS_Record",
                             domain=self.domain,
                             record=record)

    def _request_modify_dns_record(self, record):
        """Sends Modify_DNS_Record request"""
        return self._request("Modify_DNS_Record",
                             domain=self.domain,
                             record=record)

    def _request_delete_dns_record_by_id(self, identifier):
        """Sends Delete_DNS_Record request"""
        return self._request("Delete_DNS_Record",
                             domain=self.domain,
                             record={'id': identifier})

    def _request(self, command, **kwargs):
        """Make request parse response"""
        args = dict(kwargs)
        if self.ssid:
            args['ssid'] = self.ssid
        method = getattr(self.api, command)
        response = method(**args)
        self.response = response
        if response and 'status' in response:
            if response['status'] == 'error':
                raise SubregError(
                    message=response['error']['errormsg'],
                    major=response['error']['errorcode']['major'],
                    minor=response['error']['errorcode']['minor']
                )
            if response['status'] == 'ok':
                return response['data'] if 'data' in response else dict()
            else:
                raise Exception("Invalid status found in SOAP response")
        raise Exception('Invalid response')


class SubregError(Exception):
    def __init__(self, major, minor, message):
        self.major = int(major)
        self.minor = int(minor)
        self.message = message

    def __str__(self):
        return 'Major: {} Minor: {} Message: {}'.format(self.major, self.minor, self.message)
