"""Module provider for DNS.services"""

import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for DNS.services"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["dns.services"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-username", help="specify username for authentication"
        )
        parser.add_argument(
            "--auth-password", help="specify password for authentication"
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.auth_token = None
        self.domain_id = None
        self.api_endpoint = "https://dns.services/api"

    def authenticate(self):
        if self.auth_token is None:
            username = self._get_provider_option("auth_username")
            password = self._get_provider_option("auth_password")
            data = {
                "username": username,
                "password": password,
            }

            result = requests.post(self.api_endpoint + "/login", data=data)
            result.raise_for_status()
            self.auth_token = result.json()["token"]

        data = self._get("/dns")
        for zone in data["zones"]:
            if zone["name"] == self.domain:
                self.domain_id = zone["domain_id"]
                self.service_id = zone["service_id"]
                return
        raise AuthenticationError("No domain found")

    def cleanup(self) -> None:
        pass

    def create_record(self, rtype, name, content):
        print("create_record")
        # check if record already exists
        if not self.list_records(rtype, name, content):
            data = {
                "type": rtype,
                "name": self._relative_name(name),
                "content": content,
            }
            ttl = self._get_lexicon_option("ttl")
            if ttl:
                data["ttl"] = ttl
            priority = self._get_lexicon_option("priority")
            if priority:
                data["priority"] = str(priority)
            LOGGER.debug("create_record: %s", data)
            self._post(f"/service/{self.service_id}/dns/{self.domain_id}/records", data)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        print("list_records")
        payload = self._get(f"/service/{self.service_id}/dns/{self.domain_id}")
        records = []
        for _, record in payload["records"].items():
            processed_record = {
                "type": record["type"],
                "name": record["name"],
                "ttl": record["ttl"],
                "content": record["content"],
                "id": record["id"],
            }
            processed_record = self._clean_TXT_record(processed_record)
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

    # Update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        print("update_record")
        data = {
            "type": rtype,
            "name": self._relative_name(name),
            "content": content,
        }
        ttl = self._get_lexicon_option("ttl")
        if ttl:
            data["ttl"] = ttl
        priority = self._get_lexicon_option("priority")
        if priority:
            data["priority"] = str(priority)
        LOGGER.debug("update_record: %s", data)
        self._put(
            f"/service/{self.service_id}/dns/{self.domain_id}/records/{identifier}",
            data,
        )
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
            self._delete(
                f"/service/{self.service_id}/dns/{self.domain_id}/records/{record_id}"
            )

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers

    def _request(self, action="GET", url="/", data=None, query_params=None):
        print("request")
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.auth_token}",
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
