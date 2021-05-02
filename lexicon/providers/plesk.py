"""
Lexicon Plesk Provider

Author: Jens Reimann, 2018

API Docs: https://docs.plesk.com/en-US/onyx/api-rpc
"""
import logging
from collections import defaultdict
from typing import Dict, List, Optional
from xml.etree import cElementTree
from xml.etree.ElementTree import Element

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

PLEX_URL_SUFFIX = "/enterprise/control/agent.php"

NAMESERVER_DOMAINS: List[str] = []


def provider_parser(subparser):
    """Configure provider parser for Plesk"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )
    subparser.add_argument(
        "--plesk-server", help="specify URL to the Plesk Web UI, including the port"
    )


class Provider(BaseProvider):
    """Provider class for Plesk"""

    def __init__(self, config):
        super(Provider, self).__init__(config)

        self.api_endpoint = self._get_provider_option("plesk_server")

        if self.api_endpoint.endswith("/"):
            self.api_endpoint = self.api_endpoint[:-1]

        if not self.api_endpoint.endswith(PLEX_URL_SUFFIX):
            self.api_endpoint += PLEX_URL_SUFFIX

        self.domain_id = None

        self.username = self._get_provider_option("auth_username")
        assert self.username is not None

        self.password = self._get_provider_option("auth_password")
        assert self.password is not None

    def __simple_request(self, rtype, operation, req):

        response = self.__plesk_request({rtype: {operation: req}})[rtype][operation]

        result = response["result"]

        if isinstance(result, list):
            for record in result:
                if record["status"] == "error":
                    raise Exception(
                        f"API returned at least one error: {record['errtext']}"
                    )
        elif response["result"]["status"] == "error":
            errcode = response["result"]["errcode"]
            errtext = response["result"]["errtext"]
            raise Exception(f"API returned error: {errcode} ({errtext})")

        return response

    def __plesk_request(self, request):

        headers = {
            "Content-type": "text/xml",
            "HTTP_PRETTY_PRINT": "TRUE",
            "HTTP_AUTH_LOGIN": self.username,
            "HTTP_AUTH_PASSWD": self.password,
        }

        xml = f"""\
<?xml version="1.0" encoding="utf-8"?>
{cElementTree.tostring(_dict_to_etree({"packet": request}), encoding="unicode")}\
"""

        LOGGER.debug("Request: %s", xml)

        response = requests.post(
            self.api_endpoint,
            headers=headers,
            data=xml,
            auth=(self.username, self.password),
        )

        data = response.text

        LOGGER.debug("Response: %s", data)
        result = _etree_to_dict(cElementTree.XML(data))
        return result["packet"]

    def __find_site(self):
        return self.__simple_request(
            "site", "get", {"filter": {"name": self.domain, "dataset": {}}}
        )["result"]["id"]

    def _authenticate(self):
        self.domain_id = self.__find_site()

        if self.domain_id is None:
            raise AuthenticationError("Domain not found")

    def _create_record(self, rtype, name, content):
        return self.__create_entry(rtype, name, content, None)

    def _list_records(self, rtype=None, name=None, content=None):
        entries = self.__find_dns_entries(rtype, name, content)
        LOGGER.debug("list_records: %s", entries)
        return entries

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier is None:
            entries = self.__find_dns_entries(rtype, name, None)
            LOGGER.debug("Entries found: %s", entries)

            if not entries:
                raise Exception("No entry found for updating")

            identifier = entries[0]["id"]
            entry = self.__get_dns_entry(identifier)

            ids = []
            for an_entry in entries:
                ids.append(an_entry["id"])

            self.__delete_dns_records_by_id(ids)

        else:

            entry = self.__get_dns_entry(identifier)
            self.__delete_dns_records_by_id([identifier])

        assert entry is not None

        LOGGER.debug("Updating: %s", entry)

        if rtype:
            entry["type"] = rtype
        if name:
            entry["host"] = name
        if content:
            entry["value"] = content

        return self.__create_entry(
            entry["type"], entry["host"], entry["value"], entry["opt"]
        )

    def __create_entry(self, rtype, host, value, opt):
        entries = self.__find_dns_entries(rtype, self._fqdn_name(host), value)

        if entries:
            return True  # already exists

        self.__simple_request(
            "dns",
            "add_rec",
            {
                "site-id": self.domain_id,
                "type": rtype,
                "host": self._relative_name(host),
                "value": value,
                "opt": opt,
            },
        )

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            self.__delete_dns_records_by_id([identifier])
            return True
        entries = self.__find_dns_entries(rtype, self._fqdn_name(name), content)
        ids = []

        for entry in entries:
            ids.append(entry["id"])

        self.__delete_dns_records_by_id(ids)
        return bool(ids)

    def __get_dns_entry(self, identifier):
        return self.__simple_request("dns", "get_rec", {"filter": {"id": identifier}})[
            "result"
        ]["data"]

    def __find_dns_entries(self, rtype=None, host=None, value=None):
        LOGGER.debug("Searching for: %s, %s, %s", rtype, host, value)

        if value and rtype and rtype in ["CNAME"]:
            LOGGER.debug("CNAME transformation")
            value = value.rstrip(".") + "."

        if host:
            host = self._fqdn_name(host)

        result = self.__simple_request(
            "dns", "get_rec", {"filter": {"site-id": self.domain_id}}
        )

        entries = []

        for record in result["result"]:

            LOGGER.debug("Record: %s", record)

            if (rtype is not None) and (record["data"]["type"] != rtype):
                LOGGER.debug(
                    "\tType doesn't match - expected: '%s', found: '%s'",
                    rtype,
                    record["data"]["type"],
                )
                continue

            if (host is not None) and (record["data"]["host"] != host):
                LOGGER.debug(
                    "\tHost doesn't match - expected: '%s', found: '%s'",
                    host,
                    record["data"]["host"],
                )
                continue

            if (value is not None) and (record["data"]["value"] != value):
                LOGGER.debug(
                    "\tValue doesn't match - expected: '%s', found: '%s'",
                    value,
                    record["data"]["value"],
                )
                continue

            entry = {
                "id": record["id"],
                "type": record["data"]["type"],
                "name": self._full_name(record["data"]["host"]),
                "ttl": None,
                "options": {},
            }

            if record["data"]["type"] in ["CNAME"]:
                entry["content"] = record["data"]["value"].rstrip(".")
            else:
                entry["content"] = record["data"]["value"]

            if record["data"]["type"] == "MX":
                entry["options"]["mx"] = {"priority": int(record["data"]["opt"])}

            entries.append(entry)

        return entries

    def __delete_dns_records_by_id(self, ids):
        if not ids:
            return

        req = []
        for i in ids:
            req.append({"del_rec": {"filter": {"id": i}}})

        self.__plesk_request({"dns": req})

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # Helper _request is not used for Plesk provider
        pass


def _etree_to_dict(t: Element) -> Optional[Dict]:
    d: Optional[Dict] = {t.tag: {} if t.attrib else None}
    children = list(t)
    if children:
        dd = defaultdict(list)
        for dc in map(_etree_to_dict, children):
            if dc:
                for k, v in dc.items():
                    dd[k].append(v)
        d = {t.tag: {k: v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if t.attrib and d:
        d[t.tag].update(("@" + k, v) for k, v in t.attrib.items())
    if t.text and d:
        text = t.text.strip()
        if children or t.attrib:
            if text:
                d[t.tag]["#text"] = text
        else:
            d[t.tag] = text
    return d


def _dict_to_etree(d: Dict) -> Element:
    def _to_etree(d1, root):
        if not d1:
            pass
        elif isinstance(d1, str):
            root.text = d1
        elif isinstance(d1, dict):
            for k, v in d1.items():
                assert isinstance(k, str)
                if k.startswith("#"):
                    assert k == "#text" and isinstance(v, str)
                    root.text = v
                elif k.startswith("@"):
                    assert isinstance(v, str)
                    root.set(k[1:], v)
                elif isinstance(v, list):
                    for e in v:
                        _to_etree(e, cElementTree.SubElement(root, k))
                else:
                    _to_etree(v, cElementTree.SubElement(root, k))
        else:
            raise TypeError("invalid type: " + str(type(d1)))

    assert isinstance(d, dict) and len(d) == 1
    tag, body = next(iter(d.items()))
    node = cElementTree.Element(tag)
    _to_etree(body, node)
    return node
