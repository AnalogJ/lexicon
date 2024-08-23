"""Module provider for DDNS"""

import hashlib
import logging
from argparse import ArgumentParser
from typing import List

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

# dnspython is an optional dependency of lexicon; do not throw an ImportError if
# the dependency is unmet.
try:
    import dns.message
    import dns.query
    import dns.tsigkeyring
    import dns.update
    import dns.versioned
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for DDNS"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return []

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-token",
            help="specify the key used in format <alg>:<key_id>:<secret>",
        )
        parser.add_argument("--ddns-server", help="specify IP of the DDNS server")

    def __init__(self, config):
        super(Provider, self).__init__(config)
        alg, keyid, secret = self._get_provider_option("auth_token").split(":")
        self.keyring = dns.tsigkeyring.from_text({keyid: (alg, secret)})
        self.endpoint = self._get_provider_option("ddns_server")
        self.zone = self._get_provider_option("domain")
        self.cached_zone_content = {}

    def _run_query(self, message):
        return dns.query.tcp(message, self.endpoint, timeout=10)

    def authenticate(self):
        if not self.endpoint:
            raise AuthenticationError("No DDNS server provided, use --ddns-server")
        pass

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing
    def create_record(self, rtype, name, content):
        if self._get_lexicon_option("ttl"):
            ttl = self._get_lexicon_option("ttl")
        else:
            ttl = 300
        name = dns.name.from_text(name).relativize(dns.name.from_text(self.zone))

        update = dns.update.Update(self.zone, keyring=self.keyring)
        update.add(name, ttl, rtype, content)
        self._run_query(update)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        if rtype and name:  # doing a simple query is enough if we have type and name
            query = dns.message.make_query(name, rtype)
        else:  # if not, perform a zone transfert to get all records
            query = dns.xfr.make_query(
                dns.versioned.Zone(self.zone), keyring=self.keyring
            )[0]
            self.cached_zone_content = {}

        answers = self._run_query(query).answer

        records = []
        for answer in answers:  # filter unwanted results
            a_name = answer.name.to_text().rstrip(".")
            if name and name != a_name:
                continue
            a_rtype = dns.rdatatype.to_text(answer.rdtype)
            if rtype and rtype != a_rtype:
                continue
            for rdata in answer:
                rdata = rdata.to_text()
                if content and content != rdata:
                    continue
                identifier = _identifier(a_rtype, a_name, rdata)
                record = {
                    "type": a_rtype,
                    "name": a_name,
                    "ttl": answer.ttl,
                    "content": rdata,
                    "id": identifier,
                }
                records.append(record)
                self.cached_zone_content[identifier] = (a_rtype, a_name, rdata)
        LOGGER.debug("list_records: %s", records)
        LOGGER.debug("Number of records retrieved: %d", len(records))
        return records

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        if self._get_lexicon_option("ttl"):
            ttl = self._get_lexicon_option("ttl")
        else:
            ttl = 300
        if not identifier:
            rrset = self.list_records(rtype, name)
            if len(rrset) == 1:
                identifier = rrset[0]["id"]
            elif len(rrset) < 1:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )
        d_rtype, d_name, d_content = self._resolve_identifier(identifier)

        if not rtype:
            rtype = d_rtype
        if not name:
            name = d_name

        d_name = dns.name.from_text(d_name).relativize(dns.name.from_text(self.zone))
        name = dns.name.from_text(name).relativize(dns.name.from_text(self.zone))

        update = dns.update.Update(self.zone, keyring=self.keyring)
        update.delete(d_name, d_rtype, d_content)
        update.add(name, ttl, rtype, content)
        self._run_query(update)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            rtype, name, content = self._resolve_identifier(identifier)

        name = dns.name.from_text(name).relativize(dns.name.from_text(self.zone))
        update = dns.update.Update(self.zone, keyring=self.keyring)
        if content:
            update.delete(name, rtype, content)
        else:
            update.delete(name, rtype)
        self._run_query(update)

        return True

    def _resolve_identifier(self, ident):
        if not self.cached_zone_content.get(ident):
            self.list_records()  # if cache miss, reload cache
        return self.cached_zone_content[ident]

    def _request(self, action="GET", url="/", data=None, query_params=None):
        pass


def _identifier(record):
    m = hashlib.sha256()
    m.update(("type=" + record.get("type", "") + ",").encode("utf-8"))
    m.update(("name=" + record.get("name", "") + ",").encode("utf-8"))
    m.update(("content=" + record.get("content", "") + ",").encode("utf-8"))

    return m.hexdigest()[0:7]
