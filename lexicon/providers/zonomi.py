"""
Lexicon Zonomi and Rimuhosting Provider

Author: Juan Rossi, 2017

Zonomi API Docs: https://zonomi.com/app/dns/dyndns.jsp
Rimuhosting API Docs: https://rimuhosting.com/dns/dyndns.jsp

Implementation notes:
* Lots of tricks taken from the PowerDNS API
* The Zonomi API does not assign a unique identifier to each record in the way
  that Lexicon expects. We work around this by creating an ID based on the record
  name, type and content, which when taken together are always unique
* The  API has no notion of 'create a single record' or 'delete a single
  record'. All operations are either 'replace the RRSet with this new set of records'
  or 'delete all records for this name and type. Similarly, there is no notion of
  'change the content of this record', because records are identified by their name,
  type and content.
"""
import logging
from xml.etree import ElementTree

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

APIENTRYPOINT = {
    "zonomi": "https://zonomi.com/app",
    "rimuhosting": "https://rimuhosting.com",
}

NAMESERVER_DOMAINS = ["zonomi.com"]


def provider_parser(subparser):
    """Configure provider parser for Zonomi"""
    subparser.add_argument("--auth-token", help="specify token for authentication")
    subparser.add_argument(
        "--auth-entrypoint",
        help="use Zonomi or Rimuhosting API",
        choices=["zonomi", "rimuhosting"],
    )


class Provider(BaseProvider):
    """Provider class for Zonomi"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        if not self._get_provider_option("auth_token"):
            raise Exception("Error, application key is not defined")

        self.api_endpoint = APIENTRYPOINT.get("zonomi")

        if self._get_provider_option("auth_entrypoint"):
            self.api_endpoint = APIENTRYPOINT.get(
                self._get_provider_option("auth_entrypoint")
            )

    def _authenticate(self):

        payload = self._get(
            "/dns/dyndns.jsp",
            {"action": "QUERY", "name": "**." + self.domain, "type": "SOA"},
        )

        if payload.find("is_ok").text != "OK:":
            raise AuthenticationError(f"Error with api {payload.find('is_ok').text}")

        self.domain_id = self.domain

    def _make_identifier(self, rtype, name, content):
        return f"{rtype}/{self._full_name(name)}={content}"

    def _parse_identifier(self, identifier):
        parts = identifier.split("/")
        rtype = parts[0]
        parts = parts[1].split("=")
        name = parts[0]
        content = "=".join(parts[1:])
        return rtype, name, content

    def _create_record(self, rtype, name, content):
        request = {
            "action": "SET",
            "type": rtype,
            "name": self.domain,
            "value": content,
        }

        if name is not None:
            request["name"] = self._full_name(name)

        if self._get_lexicon_option("ttl"):
            request["ttl"] = self._get_lexicon_option("ttl")

        if self._get_lexicon_option("priority"):
            request["prio"] = self._get_lexicon_option("priority")

        payload = self._get("/dns/dyndns.jsp", request)

        if payload.find("is_ok").text != "OK:":
            raise Exception(f"An error occurred: {payload.find('is_ok').text}")

        LOGGER.debug("create_record: %s", True)
        return True

    def _list_records(self, rtype=None, name=None, content=None):
        records = []

        request = {"action": "QUERY", "name": "**." + self.domain}

        if rtype is not None:
            request["type"] = rtype
        if name is not None:
            request["name"] = self._full_name(name)
        if content is not None:
            request["value"] = content

        payload = self._get("/dns/dyndns.jsp", request)
        for rxml in payload.iter("record"):
            processed_record = {
                "type": rxml.attrib["type"],
                "name": rxml.attrib["name"],
                "content": rxml.attrib["content"],
                "id": self._make_identifier(
                    rxml.attrib["type"], rxml.attrib["name"], rxml.attrib["content"]
                ),
                "ttl": rxml.attrib["ttl"].split()[0],
            }
            records.append(processed_record)
        LOGGER.debug("list_records: %s", records)
        return records

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier is not None:
            rtype, name, content = self._parse_identifier(identifier)

        request = {"action": "DELETE", "name": self.domain}

        if rtype is not None:
            request["type"] = rtype
        if name is not None:
            request["name"] = self._full_name(name)
        if content is not None:
            request["value"] = content

        payload = self._get("/dns/dyndns.jsp", request)

        if payload.find("is_ok").text != "OK:":
            raise Exception(f"An error occurred: {payload.find('is_ok').text}")

        LOGGER.debug("delete_record: %s", True)
        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        self._delete_record(identifier)
        ttype, tname, tcontent = self._parse_identifier(identifier)
        request = {
            "action": "SET",
            "type": ttype,
            "name": self._full_name(tname),
            "value": tcontent,
        }

        if rtype is not None:
            request["type"] = rtype
        if name is not None:
            request["name"] = self._full_name(name)
        if content is not None:
            request["value"] = content
        if self._get_lexicon_option("ttl"):
            request["ttl"] = self._get_lexicon_option("ttl")
        if self._get_lexicon_option("priority"):
            request["prio"] = self._get_lexicon_option("priority")

        payload = self._get("/dns/dyndns.jsp", request)

        if payload.find("is_ok").text != "OK:":
            raise Exception(f"An error occurred: {payload.find('is_ok').text}")

        LOGGER.debug("update_record: %s", True)
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        else:
            query_params["api_key"] = self._get_provider_option("auth_token")

        response = requests.request(
            action, self.api_endpoint + url, params=query_params
        )
        tree = ElementTree.ElementTree(ElementTree.fromstring(response.content))
        root = tree.getroot()
        if root.tag == "error":
            raise Exception(f"An error occurred: {root.text}")
        response.raise_for_status()
        return root
