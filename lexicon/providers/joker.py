"""Module provider for Joker.com"""
# The Joker.com API is well documented.
# Several specificities compared to classic REST API in other providers:
#   - everything is done with GET requests: all parameters (including actual records data
#     and authentication data) are passed in the URLs,
#   - DNS zones are represented in a "strongly" formatted flat format (not JSON or XML) that may
#     remind a zone definition in bind9,
#   - every operation requires to pass the entire updated zone through the API, so care must be
#     taken to not alter unexpectedly other entries during the create/update/delete operations,
#   - all headers and data are contained in the response body; then this kind of body is composed
#     of several lines of type key: value containing the headers (including errors), then a blank
#     line makes the separation with the data itself (see _process_response for the body parsing).
import binascii
import json
import logging
import re

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["ns.joker.com"]

API_BASE_URL = "https://dmapi.joker.com/request"
DNSZONE_ENTRY_PATTERN = re.compile(
    r"^(.+?)\s+(\w+)\s+(.+?)\s+((?:\\\"(?:.+?)\\\")|(?:.+?))\s+(\d+)(?:\s+(\d+)\s+(\d+)\s+(.+?)|\s+(.+?)|)$"
)


def provider_parser(subparser):
    """Generate a subparser for Joker"""
    subparser.description = """
The Joker.com provider requires a valid token for authentication.
You can create one in the section 'Manage Joker.com API access keys' of 'My Profile' in your Joker.com account.
"""
    subparser.add_argument(
        "--auth-token",
        help="specify the API Key to connect to the Joker.com API",
    )


class _Response:
    def __init__(self, headers, data):
        self.headers = headers
        self.data = data

    def __str__(self):
        return json.dumps({"headers": self.headers, "data": self.data})


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self._session_id = None

    def _authenticate(self):
        auth_token = self._get_provider_option("auth_token")

        response = requests.get(API_BASE_URL + "/login", params={"api-key": auth_token})

        result = _process_response(response)
        self._session_id = result.headers["Auth-Sid"]

        response = self._get(
            "/query-domain-list", query_params={"pattern": self.domain, "showstatus": 1}
        )

        if not response.data:
            raise AuthenticationError(
                f"Domain {self.domain} is not registered with this account."
            )

        data = response.data[0]
        items = data.split(" ")
        domain_status = items[2].split(",")

        if len(set(domain_status).difference(["production", "lock", "autorenew"])) > 0:
            raise AuthenticationError(
                f"Current status for domain {self.domain} is: {items[2]}"
            )

        self.domain_id = self.domain

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if not query_params:
            query_params = {}

        query_params["auth-sid"] = self._session_id

        response = requests.get(API_BASE_URL + url, params=query_params)
        return _process_response(response)

    def _list_records(self, rtype=None, name=None, content=None):
        response = self._get("/dns-zone-get", query_params={"domain": self.domain_id})
        zone_data = _extract_zonedata(response.data)

        zone_data = [entry for entry in zone_data if entry["type"]]

        if rtype:
            zone_data = [entry for entry in zone_data if entry["type"] == rtype]
        if name:
            zone_data = [
                entry
                for entry in zone_data
                if self._full_name(entry["label"]) == self._full_name(name)
            ]
        if content:
            zone_data = [
                entry for entry in zone_data if entry["target"] == content.strip()
            ]

        records = [
            {
                "type": entry["type"],
                "name": self._full_name(entry["label"]),
                "ttl": entry["ttl"],
                "content": entry["target"],
                "id": self._identifier(entry),
            }
            for entry in zone_data
        ]

        LOGGER.debug("list_records: %s", records)

        return records

    def _create_record(self, rtype, name, content):
        if not rtype or not name or not content:
            raise Exception(
                "Error, rtype, name and content are mandatory to create a record."
            )

        response = self._get("/dns-zone-get", query_params={"domain": self.domain_id})
        zonedata = _extract_zonedata(response.data)

        new_entry = {
            "label": self._relative_name(name),
            "type": rtype,
            "pri": 0,
            "target": content,
            "ttl": self._get_lexicon_option("ttl"),
            "valid-from": None,
            "valid-to": None,
            "parameters": None,
        }

        if any(
            entry
            for entry in zonedata
            if self._identifier(new_entry) == self._identifier(entry)
        ):
            LOGGER.debug(
                "create_record (ignored, duplicate): %s", self._identifier(new_entry)
            )
            return True

        zonedata.append(new_entry)

        self._apply_zonedata(zonedata)

        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier and not (rtype and name):
            raise Exception(
                "Error, either identifier or rtype + name are mandatory to update a record."
            )

        response = self._get("/dns-zone-get", query_params={"domain": self.domain_id})
        zonedata = _extract_zonedata(response.data)

        selector_info = (
            f"identifier={identifier}" if identifier else f"type={rtype},name={name}"
        )

        if identifier:
            to_update = [
                entry for entry in zonedata if self._identifier(entry) == identifier
            ]
        else:
            to_update = [
                entry
                for entry in zonedata
                if entry["type"] == rtype
                and self._full_name(entry["label"]) == self._full_name(name)
            ]

        if not to_update:
            raise Exception(f"Error, could not find a record for {selector_info}.")

        if len(to_update) > 1:
            raise Exception(
                f"Error, found more than one record for {selector_info}. "
                "Please use an identifier to select one explicitly."
            )

        to_update[0].update(
            {
                "type": rtype if rtype else to_update[0]["type"],
                "label": self._relative_name(name) if name else to_update[0]["label"],
                "target": content if content else to_update[0]["content"],
                "ttl": self._get_lexicon_option("ttl"),
            }
        )

        self._apply_zonedata(zonedata)

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier and not rtype:
            raise Exception(
                "Error, either rtype or identifier are mandatory to delete a record."
            )

        response = self._get("/dns-zone-get", query_params={"domain": self.domain_id})
        zonedata = _extract_zonedata(response.data)

        if identifier:
            zonedata = [
                entry for entry in zonedata if self._identifier(entry) != identifier
            ]
        else:
            zonedata = [
                entry
                for entry in zonedata
                if entry["type"] is None
                or self._identifier(entry)
                != self._identifier(
                    {
                        "type": rtype,
                        "label": name if name else entry["label"],
                        "target": content if content else entry["target"],
                    }
                )
            ]

        self._apply_zonedata(zonedata)

        return True

    def _apply_zonedata(self, zonedata):
        data = []
        for entry in zonedata:
            if "raw" in entry:
                data.append(entry["raw"])
            else:
                # TXT entries always require content to be quoted
                target = (
                    f'"{entry["target"]}"'
                    if entry["type"] == "TXT"
                    else entry["target"]
                )
                line = f"{entry['label']} {entry['type']} {entry['pri']} {target} {entry['ttl']}"

                if entry["valid-from"] is not None and entry["valid-to"] is not None:
                    line = f"{line} {entry['valid-from']} {entry['valid-to']}"

                if entry["parameters"] is not None:
                    line = f"{line} {entry['parameters']}"

                data.append(line)

        self._get(
            "/dns-zone-put",
            query_params={"domain": self.domain_id, "zone": "\n".join(data)},
        )

    def _identifier(self, record):
        if "raw" in record:
            return None

        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(("type=" + record.get("type", "") + ",").encode("utf-8"))
        digest.update(
            ("name=" + self._full_name(record.get("label", "")) + ",").encode("utf-8")
        )
        digest.update(("content=" + record.get("target", "") + ",").encode("utf-8"))

        return binascii.hexlify(digest.finalize()).decode("utf-8")[0:7]

    def _relative_name(self, record_name):
        if record_name == self.domain_id:
            return "@"

        return super(Provider, self)._relative_name(record_name)

    def _full_name(self, record_name):
        if record_name == "@":
            return self.domain_id

        return super(Provider, self)._full_name(record_name)


def _extract_zonedata(data):
    processed = []

    for entry in data:
        match = DNSZONE_ENTRY_PATTERN.match(entry)

        if match:
            extracted = {
                "label": match.group(1),
                "type": match.group(2),
                "pri": match.group(3),
                "target": match.group(4),
                "ttl": int(match.group(5)),
            }

            try:
                extracted.update(
                    {
                        "parameters": match.group(9),
                        "valid-from": None,
                        "valid-to": None,
                    }
                )
            except IndexError:
                try:
                    extracted.update(
                        {
                            "parameters": match.group(8),
                            "valid-from": int(match.group(7)),
                            "valid-to": int(match.group(6)),
                        }
                    )
                except IndexError:
                    pass

            if extracted["type"] == "TXT":
                extracted["target"] = re.sub(
                    r'"(.*)"', r"\1", extracted["target"]
                ).strip()

            processed.append(extracted)
        else:
            processed.append(
                {
                    "raw": entry,
                    "type": None,
                }
            )

    return processed


def _process_response(response):
    response.raise_for_status()

    headers = {}
    body = []
    feed_headers = True

    data = response.text
    for line in data.split("\n"):
        if not line:
            feed_headers = False
            continue

        if feed_headers:
            items = line.split(":")
            headers[items[0]] = items[1].lstrip()
        else:
            body.append(line)

    processed_response = _Response(headers, body)

    if headers["Status-Code"] != "0":
        if body and body[0] == "API key is invalid":
            raise requests.exceptions.HTTPError(
                f"{headers['Status-Code']} Error: API key is invalid for url: {response.url}",
                response=processed_response,
            )
        raise requests.exceptions.HTTPError(
            f"{headers['Status-Code']} Error: {headers['Status-Text']} ({headers['Error']}) "
            f"for url: {response.url}",
            response=processed_response,
        )

    return processed_response
