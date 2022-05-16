"""Module provider for Yandex PDD

API doc: https://yandex.com/dev/domain/doc/reference/dns-add.html
"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

__author__ = "Aliaksandr Kharkevich"
__license__ = "MIT"
__contact__ = "https://github.com/kharkevich"

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["yandex.com"]


def provider_parser(subparser):
    """Generate parser provider for Yandex PDD"""
    subparser.add_argument(
        "--auth-token",
        help="specify PDD token (https://yandex.com/dev/domain/doc/concepts/access.html)",
    )


class Provider(BaseProvider):
    """Provider class for Yandex PDD"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://pddimp.yandex.ru/api2/admin/dns"

    def _authenticate(self):
        payload = self._get(f"/list?domain={self.domain}")
        if payload["success"] != "ok":
            raise AuthenticationError("No domain found")
        self.domain_id = self.domain

    def _create_record(self, rtype, name, content):
        if rtype in ("CNAME", "MX", "NS"):
            # make sure a the data is always a FQDN for CNAMe.
            content = content.rstrip(".") + "."

        querystring = f"domain={self.domain_id}&type={rtype}&subdomain={self._relative_name(name)}&content={content}"
        if self._get_lexicon_option("ttl"):
            querystring += f"&ttl={self._get_lexicon_option('ttl')}"

        payload = self._post("/add", {}, querystring)

        return self._check_exitcode(payload, "create_record")

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        url = f"/list?domain={self.domain_id}"
        records = []
        payload = {}

        next_url = url
        while next_url is not None:
            payload = self._get(next_url)
            if (
                "links" in payload
                and "pages" in payload["links"]
                and "next" in payload["links"]["pages"]
            ):
                next_url = payload["links"]["pages"]["next"]
            else:
                next_url = None

            for record in payload["records"]:
                if record["type"] == "MX":
                    assembled_content = f"{record['priority']} {record['content']}"
                if record["type"] == "SRV":
                    if "target" in record:
                        srv_target = record["target"]
                    else:
                        srv_target = record["content"]
                    assembled_content = f"{record['priority']} {record['weight']} {record['port']} {srv_target}"
                else:
                    assembled_content = record.get("content")
                record_name = (
                    f"{record['subdomain']}.{self.domain_id}"
                    if record["subdomain"] != "@"
                    else self.domain_id
                )
                processed_record = {
                    "type": record["type"],
                    "name": record_name,
                    "ttl": record["ttl"],
                    "content": assembled_content,
                    "id": record["record_id"],
                }
                records.append(processed_record)

        if rtype:
            records = [record for record in records if record["type"] == rtype]
        if name:
            records = [
                record for record in records if record["name"] == self._full_name(name)
            ]
        if content:
            records = [
                record
                for record in records
                if record["content"].lower() == content.lower()
            ]

        LOGGER.debug("list_records: %s", records)
        return records

    # Just update existing record. If Identifier is not provided, update the latest entry with matching name and rtype.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        if not identifier:
            # get existing entries, and pick the last one for update
            records = self._list_records(rtype=rtype, name=name)
            if not records:
                return False
            identifier = records[-1]["id"]

        data = ""
        if rtype:
            data += f"&type={rtype}"
        if name:
            data += f"&subdomain={self._relative_name(name)}"
        if content:
            data += f"&content={content}"

        payload = self._post(
            "/edit", {}, f"domain={self.domain_id}&record_id={identifier}" + data
        )

        return self._check_exitcode(payload, "update_record")

    # Delete an existing record.
    # If record does not exist (I'll hope), do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)

        for record_id in delete_record_id:
            self._post("/del", {}, f"domain={self.domain_id}&record_id={record_id}")

        # return self._check_exitcode(payload, 'delete_record')
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "PddToken": self._get_provider_option("auth_token"),
        }

        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        response = requests.request(
            action,
            url,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if action == "DELETE":
            return ""
        return response.json()

    def _check_exitcode(self, payload, title):
        if payload["success"] == "ok":
            LOGGER.debug("%s: %s", title, payload["success"])
            return True
        if payload["error"] == "record_exists":
            LOGGER.debug("%s: %s", title, True)
            return True
        LOGGER.debug("%s: %s", title, payload["error"])
        return False
