"""Module provider for Misaka.IO"""
from __future__ import absolute_import

import base64
import json
import logging
from typing import Tuple

import requests

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = [
    # gTLDs
    "m1ns.com",
    "m1ns.net",
    "m1ns.org",
    # new gTLDs
    "m1ns.one",
    "m1ns.moe",
    "m1ns.xyz",
    "m1ns.fyi",
    "m1ns.app",
    # ccTLDs
    "m1ns.be",
    "m1ns.io",
    "m1ns.uk",
    "m1ns.us",
    "m1ns.im",
    # for PTR zones only
    "reversedns.org",
    # legacy domains
    "ns53.net",
]


def _recordset_has_record(record_set, value):
    for record in record_set["records"]:
        if record["value"] == value:
            return True
    return False


def provider_parser(subparser):
    """Configure provider parser for Misaka.IO"""
    subparser.add_argument("--auth-token", help="specify token for authentication")


class Provider(BaseProvider):
    """Provider class for Misaka.IO"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.misaka.io/dns"

    def _authenticate(self):
        payload = self._get(f"/zones/{self.domain}/settings")
        if not payload["id"]:
            raise Exception("No domain found")

        self.domain_id = self.domain

    # Create or update a record.
    def _create_record(self, rtype, name, content):
        name = self._relative_name(name)

        identifier = self._identifier_encode(rtype, name)
        endpoint = f"/zones/{self.domain_id}/recordsets/{name}/{rtype}"
        ttl = self._get_lexicon_option("ttl")
        record = {"value": content}

        existing_recordset = self._get_recordset(name, rtype)
        if existing_recordset:
            # append if returned recordsets doesn't include the record
            if not _recordset_has_record(existing_recordset, content):
                existing_recordset["records"].append(record)
                existing_recordset["ttl"] = ttl
                self._put(endpoint, existing_recordset)
                LOGGER.debug("recordset exists, appending: %s", identifier)
            # update ttl if returned ttl doesn't match
            elif existing_recordset["ttl"] != ttl:
                existing_recordset["ttl"] = ttl
                self._put(endpoint, existing_recordset)
                LOGGER.debug("recordset exists, updating ttl: %s", identifier)
        else:
            recordset = {
                "ttl": ttl,
                "filters": [],
                "records": [record],
            }
            self._post(endpoint, recordset)
            LOGGER.debug("create_record: %s", identifier)

        return True

    def _list_records(self, rtype=None, name=None, content=None):
        params = {}
        if name:
            name = self._relative_name(name)
            params["name"] = name

        payload = self._get(f"/zones/{self.domain_id}/recordsets", query_params=params)
        records = []
        for recordset in payload["results"]:
            if not recordset["records"]:
                continue

            if name and recordset["name"] != name:
                continue

            if rtype and recordset["type"] != rtype:
                continue

            processed_recordset = {
                "name": self._full_name(recordset["name"]),
                "type": recordset["type"],
                "ttl": recordset["ttl"],
                "id": self._identifier_encode(recordset["type"], recordset["name"]),
            }

            for record in recordset["records"]:
                processed_record = {"content": record["value"]}
                processed_record.update(processed_recordset)
                records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # use relative_name only
        if name:
            name = self._relative_name(name)

        new_identifier = self._identifier_encode(rtype, name)

        if new_identifier == identifier or (rtype is None and name is None):
            # the identifier hasn't changed, or type and name are both unspecified,
            # only update the content.
            data = {"records": {"value": content}}
            target_rtype, target_name = self._identifier_decode(identifier)
            self._put(
                f"/zones/{self.domain_id}/recordsets/{target_name}/{target_rtype}", data
            )
        else:
            if not identifier:
                identifier = new_identifier
            # identifiers are different
            # get the old record, create a new one with updated data, delete the old record.
            target_rtype, target_name = self._identifier_decode(identifier)
            old_record = self._get(
                f"/zones/{self.domain_id}/recordsets/{target_name}/{target_rtype}"
            )
            self.create_record(
                rtype or old_record["type"],
                name or old_record["domain"],
                content or old_record["records"][0]["value"],
            )
            self.delete_record(identifier)

        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        should_call_delete_api = True
        if not identifier:
            if name:
                name = self._relative_name(name)
            identifier = self._identifier_encode(rtype, name)
            should_call_delete_api = not self._delete_record_with_identifier(
                identifier, rtype, name, content
            )

        if should_call_delete_api:
            rtype, name = self._identifier_decode(identifier)
            self._delete(f"/zones/{self.domain_id}/recordsets/{name}/{rtype}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # Delete an existing record if identifier isn't None.
    # it will return True if we don't need to call delete API
    def _delete_record_with_identifier(self, identifier, rtype, name, content):
        recordset = self._get_recordset(name, rtype)
        if not recordset:
            return True

        # remove corresponding record only if content isn't None
        if not content:
            return False
        recordset["records"] = [
            record for record in recordset["records"] if record["value"] != content
        ]

        if not recordset["records"]:
            return False

        rtype, name = self._identifier_decode(identifier)
        self._put(f"/zones/{self.domain_id}/recordsets/{name}/{rtype}", recordset)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        # set defaults
        data = {} if data is None else data
        query_params = {} if query_params is None else query_params

        token = self._get_provider_option("auth_token")

        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Token {token}",
        }
        default_auth = None

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
            auth=default_auth,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    def _get_recordset(self, name, rtype):
        try:
            payload = self._get(f"/zones/{self.domain_id}/recordsets/{name}/{rtype}")
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                return None
            raise

        return {
            "ttl": payload["ttl"],
            "records": payload["records"],
            "filters": payload["filters"],
        }

    def _identifier_decode(self, identifier: str) -> Tuple[str, str]:
        padding = 4 - (len(identifier) % 4)
        chain = identifier + ("=" * padding)
        decoded = base64.urlsafe_b64decode(chain)
        if not decoded:
            raise ValueError(f"Invalid identifier: {identifier}")
        extracted = decoded.decode("utf-8").split("/")
        if len(extracted) < 2:
            raise ValueError(f"Invalid identifier: {identifier}")
        return extracted[0], extracted[1]

    def _identifier_encode(self, rtype: str, name: str) -> str:
        encoded = base64.urlsafe_b64encode(
            f"{rtype}/{self._relative_name(name)}".encode("utf-8")
        )
        return encoded.decode("utf-8").rstrip("=")
