"""Module provider for Softlayer"""
import logging

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

try:
    import SoftLayer  # type: ignore
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["softlayer.com"]


def provider_parser(subparser):
    """Generate a provider parser for Softlayer"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-api-key", help="specify API private key for authentication"
    )


class Provider(BaseProvider):
    """Provider class for Softlayer"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None

        username = self._get_provider_option("auth_username")
        api_key = self._get_provider_option("auth_api_key")

        if not username or not api_key:
            raise Exception("No username and/or api key was specified")

        sl_client = SoftLayer.create_client_from_env(username=username, api_key=api_key)
        self.sl_dns = SoftLayer.managers.dns.DNSManager(sl_client)

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider,
    # so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason,
    # of if the domain does not exist.
    def _authenticate(self):
        domain = self.domain

        payload = self.sl_dns.resolve_ids(domain)

        if not payload:
            raise AuthenticationError("No domain found")
        if len(payload) > 1:
            raise AuthenticationError("Too many domains found. This should not happen")

        LOGGER.debug("domain id: %s", payload[0])
        self.domain_id = payload[0]

    # Create record. If record already exists with the same content, do nothing

    def _create_record(self, rtype, name, content):
        records = self._list_records(rtype, name, content)
        if records:
            # Nothing to do, record already exists
            LOGGER.debug("create_record: already exists")
            return True

        name = self._relative_name(name)
        ttl = self._get_lexicon_option("ttl")
        payload = self.sl_dns.create_record(self.domain_id, name, rtype, content, ttl)

        LOGGER.debug("create_record: %s", payload)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.

    def _list_records(self, rtype=None, name=None, content=None):
        ttl = None
        if name:
            name = self._relative_name(name)

        payload = self.sl_dns.get_records(self.domain_id, ttl, content, name, rtype)

        records = []
        for record in payload:
            processed_record = {
                "type": record["type"].upper(),
                "name": self._full_name(record["host"]),
                "ttl": record["ttl"],
                "content": record["data"],
                "id": record["id"],
            }
            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    # Update a record.
    # If an identifier is specified, use it, otherwise do a lookup using type and name.

    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier:
            records = self._list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            else:
                raise Exception("Record identifier could not be found.")

        record = {"id": identifier}
        if rtype:
            record["type"] = rtype
        if name:
            record["host"] = self._relative_name(name)
        if content:
            record["data"] = content
        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        self.sl_dns.edit_record(record)

        LOGGER.debug("update_record: %s", record)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)

        for record_id in delete_record_id:
            self.sl_dns.delete_record(record_id)

        LOGGER.debug("delete_record: %s", True)
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # Helper _request is not used in Softlayer
        pass
