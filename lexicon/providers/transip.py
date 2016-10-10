from __future__ import absolute_import
from .base import Provider as BaseProvider
try:
    from transip.client import DomainClient #optional dep
except ImportError:
    pass



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
            mode="readwrite",
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
        records = self.client.getInfo(self.options.get('domain')).dnsEntries
        if self._filter_records(records, type, name, content):
            # Nothing to do, record already exists
            print 'create_record: already exists'
            return True

        records.append({
            "name": self._relative_name(name),
            "type": type,
            "content": content,
            "expire": self.options.get('ttl') or 86400
        })

        self.client.setDnsEntries(self.options.get('domain'), records)
        status = len(self.list_records(type, name, content, show_output=False)) >= 1
        print "create_record: {0}".format(status)
        return status

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None, show_output=True):
        all_records = self._convert_records(self.client.getInfo(self.options.get('domain')).dnsEntries)
        records = self._filter_records(
            records=all_records,
            type=type,
            name=name,
            content=content
        )

        if show_output:
            print 'list_records: {0}'.format(records)
        return records

    # Update a record. Identifier must be specified.
    def update_record(self, identifier=None, type=None, name=None, content=None):
        if not (type or name or content):
            raise StandardError("At least one of type, name or content must be specified.")

        all_records = self.list_records(show_output=False)
        filtered_records = self._filter_records(all_records, type, name)

        for record in filtered_records:
            all_records.remove(record)
        for record in all_records:
            record['expire'] = record['ttl']
            del record['ttl']
        all_records.append({
            "name": self._relative_name(name),
            "type": type,
            "content": content,
            "expire": self.options.get('ttl') or 86400
        })

        self.client.setDnsEntries(self.options.get('domain'), all_records)
        status = len(self.list_records(type, name, content, show_output=False)) >= 1
        print "update_record: {0}".format(status)
        return status

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not (type or name or content):
            raise StandardError("At least one of type, name or content must be specified.")

        all_records = self.list_records(show_output=False)
        filtered_records = self._filter_records(all_records, type, name, content)

        for record in filtered_records:
            all_records.remove(record)
        for record in all_records:
            record['expire'] = record['ttl']
            del record['ttl']

        self.client.setDnsEntries(self.options.get('domain'), all_records)
        status = len(self.list_records(type, name, content, show_output=False)) == 0
        print "delete_record: {0}".format(status)
        return status

    def _relative_name(self, record_name):
        name = super(Provider, self)._relative_name(record_name)
        if not name:
            name = "@"
        return name

    # Convert the objects from transip to dicts, for easier processing
    def _convert_records(self, records):
        _records = []
        for record in records:
            _records.append({
                "name": record.name,
                "type": record.type,
                "content": record.content,
                "ttl": record.expire
            })
        return _records

    # Filter a list of records based on criteria
    def _filter_records(self, records, type=None, name=None, content=None):
        _records = []
        for record in records:
            if (not type or record['type'] == type) and \
               (not name or record['name'] == self._relative_name(name)) and \
               (not content or record['content'] == content):
                _records.append(record)
        return _records
