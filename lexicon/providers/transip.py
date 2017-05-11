from __future__ import absolute_import
from __future__ import print_function

import logging

from .base import Provider as BaseProvider

try:
    from transip.service.dns import DnsEntry
    from transip.service.domain import DomainService
except ImportError:
    pass

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify username used to authenticate")
    subparser.add_argument("--auth-api-key", help="specify API private key to authenticate")


class Provider(BaseProvider):

    """
    provider_options can be overwritten by a Provider to setup custom defaults.
    They will be overwritten by any options set via the CLI or Env.
    order is:

    """
    def provider_options(self):
        return {'ttl': 86400}

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.provider_name = 'transip'
        self.domain_id = None

        username = self.options.get('auth_username')
        key_file = self.options.get('auth_api_key')

        if not username or not key_file:
            raise Exception("No username and/or keyfile was specified")

        self.client = DomainService(
            login=username,
            private_key_file=key_file
        )

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider, so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason, of if the domain does not exist.
    def authenticate(self):
        ## This request will fail when the domain does not exist,
        ## allowing us to check for existence
        domain = self.options.get('domain')
        try:
            self.client.get_info(domain)
        except:
            raise
            raise Exception("Could not retrieve information about {0}, "
                                "is this domain yours?".format(domain))
        self.domain_id = domain

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        records = self.client.get_info(self.options.get('domain')).dnsEntries
        if self._filter_records(records, type, name, content):
            # Nothing to do, record already exists
            logger.debug('create_record: already exists')
            return True

        records.append(DnsEntry(**{
            "name": self._relative_name(name),
            "record_type": type,
            "content": self._bind_format_target(type, content),
            "expire": self.options.get('ttl')
        }))

        self.client.set_dns_entries(self.options.get('domain'), records)
        status = len(self.list_records(type, name, content, show_output=False)) >= 1
        logger.debug('create_record: %s', status)
        return status

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None, show_output=True):
        all_records = self._convert_records(self.client.get_info(self.options.get('domain')).dnsEntries)
        records = self._filter_records(
            records=all_records,
            type=type,
            name=name,
            content=content
        )

        if show_output:
            logger.debug('list_records: %s', records)
        return records

    # Update a record. Identifier must be specified.
    def update_record(self, identifier=None, type=None, name=None, content=None):
        if not (type or name or content):
            raise Exception("At least one of type, name or content must be specified.")

        all_records = self.list_records(show_output=False)
        filtered_records = self._filter_records(all_records, type, name)

        for record in filtered_records:
            all_records.remove(record)
        all_records.append({
            "name": name,
            "type": type,
            "content": self._bind_format_target(type, content),
            "ttl": self.options.get('ttl')
        })


        self.client.set_dns_entries(self.options.get('domain'), self._convert_records_back(all_records))
        status = len(self.list_records(type, name, content, show_output=False)) >= 1
        logger.debug('update_record: %s', status)
        return status

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not (type or name or content):
            raise Exception("At least one of type, name or content must be specified.")

        all_records = self.list_records(show_output=False)
        filtered_records = self._filter_records(all_records, type, name, content)

        for record in filtered_records:
            all_records.remove(record)

        self.client.set_dns_entries(self.options.get('domain'), self._convert_records_back(all_records))
        status = len(self.list_records(type, name, content, show_output=False)) == 0
        logger.debug('delete_record: %s', status)
        return status

    def _full_name(self, record_name):
        if record_name == "@":
            record_name = self.options['domain']
        return super(Provider, self)._full_name(record_name)

    def _relative_name(self, record_name):
        name = super(Provider, self)._relative_name(record_name)
        if not name:
            name = "@"
        return name

    def _bind_format_target(self, type, target):
        if type == "CNAME" and not target.endswith("."):
            target += "."
        return target

    # Convert the objects from transip to dicts, for easier processing
    def _convert_records(self, records):
        _records = []
        for record in records:
            _records.append({
                "id": "{0}-{1}".format(self._full_name(record.name), record.type),
                "name": self._full_name(record.name),
                "type": record.type,
                "content": record.content,
                "ttl": record.expire
            })
        return _records

    def _to_dns_entry(self, _entry):
        return DnsEntry(self._relative_name(_entry['name']), _entry['ttl'], _entry['type'], _entry['content'])
    def _convert_records_back(self, _records):
        return [self._to_dns_entry(record) for record in _records]

    # Filter a list of records based on criteria
    def _filter_records(self, records, type=None, name=None, content=None):
        _records = []
        for record in records:
            if (not type or record['type'] == type) and \
               (not name or record['name'] == self._full_name(name)) and \
               (not content or record['content'] == content):
                _records.append(record)
        return _records
