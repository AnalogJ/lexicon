"""Module provider for luadns"""
import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for luadns"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["luadns.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-username", help="specify email address for authentication"
        )
        parser.add_argument("--auth-token", help="specify token for authentication")

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.luadns.com/v1"

    def authenticate(self):
        payload = self._get("/zones")

        domain_info = next(
            (domain for domain in payload if domain["name"] == self.domain), None
        )

        if not domain_info:
            raise AuthenticationError("No domain found")

        self.domain_id = domain_info["id"]

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing'

    def create_record(self, rtype, name, content):
        # check if record already exists
        existing_records = self.list_records(rtype, name, content)
        if len(existing_records) == 1:
            return True

        self._post(
            f"/zones/{self.domain_id}/records",
            {
                "type": rtype,
                "name": self._fqdn_name(name),
                "content": content,
                "ttl": self._get_lexicon_option("ttl"),
            },
        )

        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        payload = self._get(f"/zones/{self.domain_id}/records")

        records = []
        for record in payload:
            if "id" in record:
                processed_record = {
                    "id": record["id"],
                    "type": record["type"],
                    "name": self._full_name(record["name"]),
                    "ttl": record["ttl"],
                    "content": record["content"],
                }
                records.append(processed_record)

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

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        data = {"ttl": self._get_lexicon_option("ttl")}
        if rtype:
            data["type"] = rtype
        if name:
            data["name"] = self._fqdn_name(name)
        if content:
            data["content"] = content

        self._put(f"/zones/{self.domain_id}/records/{identifier}", data)

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

        for record_id in delete_record_id:
            self._delete(f"/zones/{self.domain_id}/records/{record_id}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            auth=requests.auth.HTTPBasicAuth(
                self._get_provider_option("auth_username"),
                self._get_provider_option("auth_token"),
            ),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()
