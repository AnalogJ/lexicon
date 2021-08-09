"""Module provider for Transip"""
import logging
from typing import List

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

# Support various versions of Transip Python API
try:
    from transip.service.objects import DnsEntry  # type: ignore
except ImportError:
    try:
        from transip.service.dns import DnsEntry  # type: ignore
    except ImportError:
        pass

try:
    from transip.service.domain import DomainService  # type: ignore
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS: List[str] = []


def provider_parser(subparser):
    """Configure provider parser for Transip"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-api-key", help="specify API private key for authentication"
    )


class Provider(BaseProvider):
    """
    Provider class for Transip

    provider_options can be overwritten by a Provider to setup custom defaults.
    They will be overwritten by any options set via the CLI or Env.
    order is:

    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.provider_name = "transip"
        self.domain_id = None

        username = self._get_provider_option("auth_username")
        key_file = self._get_provider_option("auth_api_key")

        if not username or not key_file:
            raise Exception("No username and/or keyfile was specified")

        self.client = DomainService(login=username, private_key_file=key_file)

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider,
    # so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason,
    # of if the domain does not exist.
    def _authenticate(self):
        # This request will fail when the domain does not exist,
        # allowing us to check for existence
        try:
            self.client.get_info(self.domain)
        except BaseException:
            raise AuthenticationError(
                f"Could not retrieve information about {self.domain}, is this domain yours?"
            )
        self.domain_id = self.domain

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        records = self.client.get_info(self.domain).dnsEntries

        if self._filter_records(records, rtype, name, content):
            # Nothing to do, record already exists
            LOGGER.debug("create_record: already exists")
            return True

        records.append(
            DnsEntry(
                **{
                    "name": self._relative_name(name),
                    "record_type": rtype,
                    "content": self._bind_format_target(rtype, content),
                    "expire": self._get_lexicon_option("ttl"),
                }
            )
        )

        self.client.set_dns_entries(self.domain, records)
        status = (
            len(self._list_records_internal(rtype, name, content, show_output=False))
            >= 1
        )
        LOGGER.debug("create_record: %s", status)
        return status

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        return self._list_records_internal(rtype=rtype, name=name, content=content)

    def _list_records_internal(
        self, rtype=None, name=None, content=None, show_output=True
    ):
        all_records = self._convert_records(
            self.client.get_info(self.domain).dnsEntries
        )
        records = self._filter_records(
            records=all_records, rtype=rtype, name=name, content=content
        )

        if show_output:
            LOGGER.debug("list_records: %s", records)
        return records

    # Update a record. Identifier must be specified.
    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        if not (rtype or name or content):
            raise Exception("At least one of rtype, name or content must be specified.")

        all_records = self._list_records_internal(show_output=False)
        filtered_records = self._filter_records(all_records, rtype, name)

        for record in filtered_records:
            all_records.remove(record)
        all_records.append(
            {
                "name": name,
                "type": rtype,
                "content": self._bind_format_target(rtype, content),
                "ttl": self._get_lexicon_option("ttl"),
            }
        )

        self.client.set_dns_entries(
            self.domain, self._convert_records_back(all_records)
        )
        status = (
            len(self._list_records_internal(rtype, name, content, show_output=False))
            >= 1
        )
        LOGGER.debug("update_record: %s", status)
        return status

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if not (rtype or name or content):
            raise Exception("At least one of rtype, name or content must be specified.")

        all_records = self._list_records_internal(show_output=False)
        filtered_records = self._filter_records(all_records, rtype, name, content)

        for record in filtered_records:
            all_records.remove(record)

        self.client.set_dns_entries(
            self.domain, self._convert_records_back(all_records)
        )
        status = (
            len(self._list_records_internal(rtype, name, content, show_output=False))
            == 0
        )
        LOGGER.debug("delete_record: %s", status)
        return status

    def _full_name(self, record_name):
        if record_name == "@":
            record_name = self.domain
        return super(Provider, self)._full_name(record_name)

    def _relative_name(self, record_name):
        name = super(Provider, self)._relative_name(record_name)
        if not name:
            name = "@"
        return name

    def _bind_format_target(self, rtype, target):
        if rtype == "CNAME" and not target.endswith("."):
            target += "."
        return target

    # Convert the objects from transip to dicts, for easier processing
    def _convert_records(self, records):
        _records = []
        for record in records:
            _records.append(
                {
                    "id": f"{self._full_name(record.name)}-{record.type}",
                    "name": self._full_name(record.name),
                    "type": record.type,
                    "content": record.content,
                    "ttl": record.expire,
                }
            )
        return _records

    def _to_dns_entry(self, _entry):
        return DnsEntry(
            self._relative_name(_entry["name"]),
            _entry["ttl"],
            _entry["type"],
            _entry["content"],
        )

    def _convert_records_back(self, _records):
        return [self._to_dns_entry(record) for record in _records]

    # Filter a list of records based on criteria
    def _filter_records(self, records, rtype=None, name=None, content=None):
        _records = []
        for record in records:
            if (
                (not rtype or record["type"] == rtype)
                and (
                    not name or self._full_name(record["name"]) == self._full_name(name)
                )
                and (not content or record["content"] == content)
            ):
                _records.append(record)
        return _records

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # Helper _request is not used in Transip.
        pass
