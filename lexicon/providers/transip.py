"""Module provider for TransIP"""
import binascii
import json
import logging
import uuid
from base64 import b64decode, b64encode
from typing import Any, Dict, List, Optional

import requests
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key

try:
    from simplejson import JSONDecodeError
except ImportError:
    from json import JSONDecodeError  # type: ignore[misc]

from lexicon.exceptions import LexiconError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS: List[str] = []

API_BASE_URL = "https://api.transip.nl/v6"


def provider_parser(subparser):
    """Configure provider parser for TransIP"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-api-key",
        help="specify the private key to use for API authentication, in PEM format: can be either "
        "the path of the key file (eg. /tmp/key.pem) or the base64 encoded content of this "
        "file prefixed by 'base64::' (eg. base64::eyJhbGciOyJ...)",
    )
    subparser.add_argument(
        "--auth-key-is-global",
        action="store_true",
        help="set this flag is the private key used is a global key with no IP whitelist restriction",
    )


class Provider(BaseProvider):
    """
    Provider class for TransIP

    provider_options can be overwritten by a Provider to setup custom defaults.
    They will be overwritten by any options set via the CLI or Env.
    order is:

    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.provider_name = "transip"
        self.domain_id = None

        private_key_conf = self._get_provider_option("auth_api_key")
        if private_key_conf.startswith("base64::"):
            private_key_bytes = b64decode(private_key_conf.replace("base64::", ""))
        else:
            with open(
                private_key_conf,
                "rb",
            ) as file:
                private_key_bytes = file.read()

        self.private_key = load_pem_private_key(private_key_bytes, password=None)
        self.token: str

    def _authenticate(self):
        request_body = {
            "login": self._get_provider_option("auth_username"),
            "nonce": uuid.uuid4().hex,
            "global_key": self._get_provider_option("auth_key_is_global") or False,
        }

        request_body_bytes = json.dumps(request_body).encode()

        signature = self.private_key.sign(
            request_body_bytes,
            padding.PKCS1v15(),
            hashes.SHA512(),
        )

        headers = {"Signature": b64encode(signature).decode()}

        response = requests.request(
            "POST", f"{API_BASE_URL}/auth", json=request_body, headers=headers
        )
        response.raise_for_status()

        self.token = response.json()["token"]

        data = self._get(f"/domains/{self.domain}")

        self.domain_id = data["domain"]["authCode"]

    def _create_record(self, rtype: str, name: str, content: str) -> bool:
        if not rtype or not name or not content:
            raise Exception(
                "Error, rtype, name and content are mandatory to create a record."
            )

        identifier = Provider._identifier(
            {"type": rtype, "name": self._full_name(name), "content": content}
        )

        if any(
            record
            for record in self._list_records(rtype=rtype, name=name, content=content)
            if record["id"] == identifier
        ):
            LOGGER.debug("create_record (ignored, duplicate): %s", identifier)
            return True

        data = {
            "dnsEntry": {
                "type": rtype,
                "name": self._relative_name(name),
                "content": content,
                "expire": self._get_lexicon_option("ttl"),
            },
        }

        self._post(f"/domains/{self.domain}/dns", data=data)

        LOGGER.debug("create_record: %s", identifier)

        return True

    def _list_records(
        self,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        data = self._get(f"/domains/{self.domain}/dns")

        records = []
        for entry in data["dnsEntries"]:
            record = {
                "type": entry["type"],
                "name": self._full_name(entry["name"]),
                "ttl": entry["expire"],
                "content": entry["content"],
            }
            record["id"] = Provider._identifier(record)
            records.append(record)

        if rtype:
            records = [record for record in records if record["type"] == rtype]
        if name:
            records = [
                record for record in records if record["name"] == self._full_name(name)
            ]
        if content:
            records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: %s", records)

        return records

    def _update_record(
        self,
        identifier: Optional[str] = None,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        if not identifier and (not rtype or not name):
            raise Exception("Error, identifier or rtype+name parameters are required.")

        if identifier:
            records = self._list_records()
            records_to_update = [
                record for record in records if record["id"] == identifier
            ]
        else:
            records_to_update = self._list_records(rtype=rtype, name=name)

        if not records_to_update:
            raise Exception(
                f"Error, could not find a record for given identifier: {identifier}"
            )

        if len(records_to_update) > 1:
            LOGGER.warning(
                "Warning, multiple records found for given parameters, "
                "only first one will be updated: %s",
                records_to_update,
            )

        record = records_to_update[0]

        # TransIP API is not designed to update one record out of several records
        # matching the same type+name (eg. multi-valued TXT entries).
        # To circumvent the limitation, we remove first the record to update, then
        # recreate it with the updated content.

        data = {
            "dnsEntry": {
                "type": record["type"],
                "name": self._relative_name(record["name"]),
                "content": record["content"],
                "expire": record["ttl"],
            },
        }

        self._request("DELETE", f"/domains/{self.domain}/dns", data=data)

        data["dnsEntry"]["content"] = content

        self._post(f"/domains/{self.domain}/dns", data=data)

        LOGGER.debug("update_record: %s", record["id"])

        return True

    def _delete_record(
        self,
        identifier: Optional[str] = None,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        if identifier:
            records = self._list_records()
            records = [record for record in records if record["id"] == identifier]

            if not records:
                raise LexiconError(
                    f"Could not find a record matching the identifier provider: {identifier}"
                )
        else:
            records = self._list_records(rtype, name, content)

        for record in records:
            data = {
                "dnsEntry": {
                    "type": record["type"],
                    "name": self._relative_name(record["name"]),
                    "content": record["content"],
                    "expire": record["ttl"],
                },
            }

            self._request("DELETE", f"/domains/{self.domain}/dns", data=data)

        LOGGER.debug("delete_records: %s %s %s %s", identifier, rtype, name, content)

        return True

    def _request(
        self,
        action: str = "GET",
        url: str = "/",
        data: Optional[Dict] = None,
        query_params: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        response = requests.request(
            action,
            f"{API_BASE_URL}{url}",
            params=query_params,
            json=data,
            headers={"Authorization": f"Bearer {self.token}"},
        )

        response.raise_for_status()

        try:
            return response.json()
        except JSONDecodeError:
            return None

    @staticmethod
    def _identifier(record):
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(("type=" + record.get("type", "") + ",").encode("utf-8"))
        digest.update(("name=" + record.get("name", "") + ",").encode("utf-8"))
        digest.update(("content=" + record.get("content", "") + ",").encode("utf-8"))

        return binascii.hexlify(digest.finalize()).decode("utf-8")[0:7]
