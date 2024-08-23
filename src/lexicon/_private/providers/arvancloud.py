"""Module provider for Arvancloud"""

import json
import logging
from argparse import ArgumentParser
from typing import Any, List, Optional

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Arvancloud"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["arvancloud.ir"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-token",
            help="specify key for authentication (API Key)",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://napi.arvancloud.ir/cdn/4.0"

    def authenticate(self):
        payload = self._get(f"/domains/{self.domain}")

        if payload["data"]["domain"] == self.domain:
            self.domain_id = self.domain
        else:
            raise AuthenticationError("No matching domain found")

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing.
    def create_record(self, rtype, name, content):
        record = self._to_r1c_record(rtype, name, content)

        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        created = True

        try:
            self._post(f"/domains/{self.domain_id}/dns-records", record)
        except requests.exceptions.HTTPError as err:
            # HTTP 422 is expected when a record with the same type and content is exists.
            if (
                err.response.status_code == 422
                and isinstance(err.response.json()["errors"], dict)
                and err.response.json()["errors"].get("name")
                and err.response.json()["errors"]["name"][0]
                == "DNS Record Data is duplicate."
            ):
                created = True
            else:
                raise Exception("create_record: %s", err.response.json()["errors"])

        LOGGER.debug("create_record: %s", created)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        filter = {"per_page": 20}

        if rtype:
            filter["type"] = rtype.lower()
        if name:
            filter["search"] = self._relative_name(name)

        records = []

        while True:
            payload = self._get(f"/domains/{self.domain_id}/dns-records", filter)

            LOGGER.debug("payload: %s", payload)

            for record in payload["data"]:
                processed_record = {
                    "type": record["type"].upper(),
                    "name": self._full_name(record["name"]),
                    "ttl": record["ttl"],
                    "content": self._parse_r1c_response(
                        record["type"].upper(), record["value"]
                    ),
                    "id": record["id"],
                }
                records.append(processed_record)

            if content:
                records = [record for record in records if record["content"] == content]

            pages = payload["meta"]["total"]
            page = payload["meta"]["current_page"]

            if page >= pages:
                break

            filter["page"] = page + 1

        LOGGER.debug("list_records: %s", records)
        LOGGER.debug("Number of records retrieved: %d", len(records))
        return records

    # Update a record.
    def update_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier:
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

        record = self._to_r1c_record(rtype, name, content)

        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        try:
            self._put(f"/domains/{self.domain_id}/dns-records/{identifier}", record)
        except requests.exceptions.HTTPError as err:
            raise Exception("update_record: %s", err.response.json()["errors"])

        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []

        if not identifier:
            records = self.list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)

        try:
            for record_id in delete_record_id:
                self._delete(f"/domains/{self.domain_id}/dns-records/{record_id}")
        except requests.exceptions.HTTPError as err:
            raise Exception("delete_record: %s", err.response.json()["errors"])

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"{self._get_provider_option('auth_token')}",
        }
        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=headers,
        )

        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    # Takes record input and puts it into a format the Arvancloud API supports
    def _to_r1c_record(self, rtype, name, content):
        if rtype in ["LOC", "SSHFP"]:
            raise NotImplementedError(f"The {rtype} isn't available for Arvancloud")
        output = {"type": rtype}

        if name is not None:
            output["name"] = self._relative_name(name)

        content_split = content.split(" ")

        if rtype in ["A", "AAAA"]:
            if len(content_split) == 1:
                output.update(
                    {
                        "value": [{"ip": content_split[0]}],
                    }
                )
            else:
                output.update(
                    {
                        "value": [
                            {"ip": ip, "port": int(port), "weight": int(weight)}
                            for ip, port, weight in content_split
                        ],
                    }
                )

        output.update(
            {
                "CNAME": (
                    lambda: {
                        "value": {
                            "host": content_split[0],
                            "host_header": (
                                content_split[1]
                                if len(content_split) == 2
                                else "source"
                            ),
                        }
                    }
                ),
                "ANAME": (
                    lambda: {
                        "value": {
                            "location": content_split[0],
                            "host_header": content_split[1],
                        }
                    }
                ),
                "MX": (
                    lambda: {
                        "value": {
                            "host": content_split[0],
                            "priority": content_split[1],
                        }
                    }
                ),
                "NS": (lambda: {"value": {"host": content}}),
                "PTR": (lambda: {"value": {"domain": content}}),
                "SRV": (
                    lambda: {
                        "value": {
                            "target": content_split[0],
                            "port": content_split[1],
                            "weight": content_split[2],
                            "priority": content_split[3],
                        }
                    }
                ),
                "TXT": (lambda: {"value": {"text": content}}),
                "SPF": (lambda: {"value": {"text": content}}),
                "DKIM": (lambda: {"value": {"text": content}}),
            }.get(rtype, lambda: {})()
        )

        return output

    # Takes record's value and puts it into a format the lexicon supports
    def _parse_r1c_response(self, rtype: str, input: Any) -> Optional[str]:
        if rtype == "CNAME" or rtype == "NS":
            return input["host"]

        if rtype == "TXT":
            return input["text"]

        if rtype == "A":
            return ", ".join(
                [
                    " ".join(
                        (str(value) if value is not None and value != "" else "")
                        for value in item.values()
                    )
                    for item in input
                ]
            )

        return None
