from __future__ import absolute_import
from .base import Provider as BaseProvider
from transip.client import DomainClient


def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify username used to authenticate")
    subparser.add_argument("--auth-api-key", help="specify API private key to authenticate")
    subparser.add_argument("--auth-ca-bundle", help="specify CA bundle to use to verify API SSL certificate")


class Provider(BaseProvider):
    def __init__(self, options):
        super(Provider, self).__init__(options)
        self.provider_name = 'transip'
        self.domain_id = None
        username = self.options.get('auth_username')
        key_file = self.options.get('auth_api_key')

        if not username or not key_file:
            raise StandardError("No username and/or keyfile was specified")

        self.client = DomainClient(
            username=username,
            key_file=key_file,
            mode="readonly",
            cacert=self.options.get('auth_ca_bundle', False)
        )

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider, so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason, of if the domain does not exist.
    def authenticate(self):
        ## This request will fail when the domain does not exist,
        ## allowing us to check for existence
        self.client.getInfo(self.options.get('domain'))

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        raise NotImplementedError("Providers should implement this!")

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        records = self._filter_records(
            records=self.client.getInfo(self.options.get('domain')).dnsEntries,
            type=type,
            name=name,
            content=content
        )

        print 'list_records: {0}'.format(records)
        return records

    # Update a record. Identifier must be specified.
    def update_record(self, identifier, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")

    def _filter_records(self, records, type=None, name=None, content=None):
        _records = []
        for record in records:
            if (not type or record.type == type) and \
               (not name or record.name == self._relative_name(name)) and \
               (not content or record.content == content):
                _records.append({
                    "name": record.name,
                    "type": record.type,
                    "content": record.content,
                    "ttl": record.expire
                })
        return _records
