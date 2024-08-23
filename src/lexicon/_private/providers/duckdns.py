"""\
Module provider for Duck DNS

The Duck DNS public API does not provide the whole set of features
supported by Lexicon: it only has one GET endpoint, "/update", authenticated by
the token which is given when you register with one of the supported
OAuth providers; the API only supports A, AAAA and TXT records, and
there is no other property that can be changed, like the TTL for these records;
the response message is plain text with "OK" or "KO" and only adds minimal
information when you supply the "verbose" parameter.

The DNS implementation supports only one record of each type
for each registered subdomain, and the value is propagated to every subdomain
after that, e.g. queries for testlexicon.duckdns.org and
example.given.testlexicon.duckdns.org return the same value.

Quirks of the DNS implementation:
* The A and AAAA records can be created separately, but when you delete one
the other is also deleted.
* When the A or AAAA records exist the TXT record is always present. Even if
you delete it will still be present with the value "". The implementation of
_list_records and _delete_record does not handle this special case.\
"""

import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

try:
    import dns.name
    import dns.resolver
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Duck DNS"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["ca-central-1.compute.amazonaws.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-token", help="specify the account token for authentication"
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_url = "https://www.duckdns.org"

    @staticmethod
    def _get_duckdns_domain(domain):
        domain_dns = dns.name.from_text(domain)

        if len(domain_dns.labels) > 2 and b"duckdns" not in domain_dns.labels:
            raise Exception("{} is not a valid Duck DNS domain.".format(domain))

        if b"duckdns" in domain_dns.labels:
            # use only the third level domain, the one actually registered in Duck DNS
            domain_index = domain_dns.labels.index(b"duckdns") - 1
        else:
            # use the last name if it is relative
            domain_index = -2

        return domain_dns.labels[domain_index].decode("utf-8")

    @staticmethod
    def _get_duckdns_rtype_param(rtype):
        if rtype not in ["A", "AAAA", "TXT"]:
            raise Exception("Duck DNS only supports A, AAAA and TXT records.")

        if rtype == "A":
            return "ip"
        elif rtype == "AAAA":
            return "ipv6"
        elif rtype == "TXT":
            return "txt"

    @staticmethod
    def _get_dns_record(name, rtype):
        if rtype not in ["A", "AAAA", "TXT"]:
            raise Exception("Duck DNS only supports A, AAAA and TXT records.")

        try:
            dns_rrset = Provider._get_dns_rrset(name, rtype)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return {}

        ttl = dns_rrset.ttl

        if rtype == "A":
            content = dns_rrset[0].address
        elif rtype == "AAAA":
            content = dns_rrset[0].address
        else:
            content = dns_rrset[0].strings[0].decode("utf-8")

        record = {
            "id": rtype,
            "type": rtype,
            "name": name,
            "ttl": ttl,
            "content": content,
        }
        return record

    @staticmethod
    def _get_dns_rrset(name, rtype):
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 60
        resolver.timeout = 70
        return resolver.resolve(name, rtype).rrset

    def authenticate(self):
        if self._get_provider_option("auth_token") is None:
            raise AuthenticationError("Must provide account token")

    def cleanup(self) -> None:
        pass

    # Create record. If the record already exists with the same content, do nothing"
    def create_record(self, rtype, name, content):
        if self._get_lexicon_option("ttl"):
            LOGGER.warning(
                "create_record: Duck DNS does not support modifying the TTL, ignoring {}".format(
                    self._get_lexicon_option("ttl")
                )
            )

        if rtype not in ["A", "AAAA", "TXT"]:
            raise Exception("Duck DNS only supports A, AAAA and TXT records.")

        if rtype == "A" and content == "auto":
            duckdns_content = ""
        else:
            duckdns_content = content

        params = {
            "domains": Provider._get_duckdns_domain(self.domain),
            Provider._get_duckdns_rtype_param(rtype): duckdns_content,
        }

        result = self._api_call(params)

        LOGGER.debug("create_record: %s", result)
        return "OK" in result

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        duckdns_domain = Provider._get_duckdns_domain(self.domain)
        full_duckdns_domain = duckdns_domain + ".duckdns.org"

        records = [
            Provider._get_dns_record(full_duckdns_domain, rtype)
            for rtype in ["A", "AAAA", "TXT"]
        ]
        processed_records = [
            {
                "id": record["id"],
                "type": record["type"],
                "name": self._full_name(name) if name is not None else record["name"],
                "ttl": record["ttl"],
                "content": record["content"],
            }
            for record in records
            if "id" in record
        ]
        filtered_records = [
            record
            for record in processed_records
            if (
                (rtype is None or record["type"] == rtype)
                and (name is None or record["name"] == self._full_name(name))
                and (content is None or record["content"] == content)
            )
        ]

        LOGGER.debug("list_records: %s", filtered_records)
        return filtered_records

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        if self._get_lexicon_option("ttl"):
            LOGGER.warning(
                "update_record: Duck DNS does not support modifying the TTL, ignoring {}".format(
                    self._get_lexicon_option("ttl")
                )
            )

        if not identifier:
            identifier = self._get_record_identifier(rtype=rtype, name=name)

        if rtype == "A" and content == "auto":
            duckdns_content = ""
        else:
            duckdns_content = content

        params = {
            "domains": Provider._get_duckdns_domain(self.domain),
            Provider._get_duckdns_rtype_param(identifier): duckdns_content,
        }

        result = self._api_call(params)

        LOGGER.debug("update_record: %s", result)
        return "OK" in result

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier:
            identifier = self._get_record_identifier(
                rtype=rtype, name=name, content=content, delete=True
            )
        if identifier is None:
            LOGGER.debug("delete_record: no record found")
            return True

        params = {
            "domains": Provider._get_duckdns_domain(self.domain),
            Provider._get_duckdns_rtype_param(identifier): "",
            "clear": "true",
        }
        result = self._api_call(params)

        LOGGER.debug("delete_record: %s", result)
        return "OK" in result

    # Helpers
    def _api_call(self, params):
        response = self._request(query_params=dict(params.items()))

        content = response.content.decode("utf-8")

        if "KO" in content:
            raise Exception("KO: {}".format(params))

        return content

    def _full_name(self, record_name):
        record_name = record_name.rstrip(".")
        full_domain = Provider._get_duckdns_domain(self.domain) + ".duckdns.org"

        if not record_name.endswith(full_domain):
            record_name = f"{record_name}.{full_domain}"
        return record_name

    def _get_record_identifier(self, rtype=None, name=None, content=None, delete=False):
        records = self.list_records(rtype=rtype, name=name, content=content)
        if len(records) == 1:
            return records[0]["id"]

        if delete and len(records) == 0:
            return None
        else:
            raise Exception("Unambiguous record could not be found.")

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if query_params is None:
            query_params = {}
        query_params["token"] = self._get_provider_option("auth_token")
        query_params["verbose"] = "true"
        response = requests.request(
            "GET",
            self.api_url + "/update",
            params=query_params,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response
