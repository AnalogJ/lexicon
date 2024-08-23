"""Module provider for Flexible Engine Cloud"""

import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Flexible Engine Cloud"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["orange-business.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument("--auth-token", help="specify token for authentication")
        parser.add_argument(
            "--zone-id",
            help="specify the zone id",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = "https://dns.prod-cloud-ocb.orange-business.com/v2"
        self.domain_id = None

    def authenticate(self):
        zone_id = self._get_provider_option("zone_id")
        payload = self._get("/zones", {"name": self.domain})

        if not zone_id:
            if not payload["zones"]:
                raise AuthenticationError("No domain found")
            if len(payload["zones"]) > 1:
                raise AuthenticationError(
                    "Too many domains found. This should not happen"
                )
            self.domain_id = payload["zones"][0]["id"]
            self.domain = payload["zones"][0]["name"].rstrip(".")
        else:
            self.domain_id = zone_id
            self.domain = payload["zones"][0]["name"].rstrip(".")

    def cleanup(self) -> None:
        pass

    def create_record(self, rtype, name, content):
        # put string in array
        tmp = content
        content = []
        content.append(tmp)

        record = {"type": rtype, "name": self._full_name(name), "records": content}

        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        if rtype == "TXT":
            # Convert "String" to "\"STRING\""
            tmp = []
            tmp.append('"' + record["records"][0] + '"')
            record["records"] = tmp
        try:
            self._post(f"/zones/{self.domain_id}/recordsets", record)
        except requests.exceptions.HTTPError as err:
            already_exists = next(
                (
                    True
                    for error in err.response.json()
                    if err.response.json()["code"] == "DNS.0312"
                ),
                False,
            )
            if not already_exists:
                raise

        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.

    def list_records(self, rtype=None, name=None, content=None):
        url = f"/zones/{self.domain_id}/recordsets"
        records = []
        payload = {}

        # Convert it to Array if it is not converted yet.
        if isinstance(content, str):
            tmp = content
            content = []
            content.append(tmp)

        # Iterating recordsets
        next_url = url
        while next_url is not None:
            payload = self._get(next_url)
            if "links" in payload and "next" in payload["links"]:
                next_url = payload["links"]["next"]
            else:
                next_url = None

            for record in payload["recordsets"]:
                processed_record = {
                    "type": record["type"],
                    "name": f"{record['name']}",
                    "ttl": record["ttl"],
                    "content": record["records"],
                    "id": record["id"],
                }
                records.append(processed_record)

        if rtype:
            records = [record for record in records if record["type"] == rtype]

        if name:
            records = [
                record
                for record in records
                if record["name"].rstrip(".") == self._full_name(name)
            ]

        if content:
            if len(content) > 1:
                records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: %s", records)
        return records

    # update a record.

    def update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier is None:
            records = self.list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            elif len(records) < 1:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )

        data = {}

        if name:
            data["name"] = name

        if rtype:
            data["type"] = rtype

        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        if content:
            if rtype == "TXT":
                content = '"' + content + '"'
            tmp = content
            content = []
            content.append(tmp)
            data["records"] = content

        self._put(f"/zones/{self.domain_id}/recordsets/{identifier}", data)
        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []

        tmp = content
        content = []
        content.append(tmp)

        if not identifier:
            records = self.list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)
        for record_id in delete_record_id:
            self._delete(f"/zones/{self.domain_id}/recordsets/{record_id}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # API requests
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Auth-Token": f"{self._get_provider_option('auth_token')}",
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
        response.raise_for_status()
        if action == "DELETE":
            return ""
        return response.json()
