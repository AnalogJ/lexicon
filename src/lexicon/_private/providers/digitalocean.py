"""Module provider for Digital Ocean"""
import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Digital Ocean"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["digitalocean.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument("--auth-token", help="specify token for authentication")

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.digitalocean.com/v2"

    def authenticate(self):
        self._get(f"/domains/{self.domain}")
        self.domain_id = self.domain

    def cleanup(self) -> None:
        pass

    def create_record(self, rtype, name, content):
        # check if record already exists
        ttl = self._get_lexicon_option("ttl")

        if not self.list_records(rtype, name, content):
            record = {
                "type": rtype,
                "name": self._relative_name(name),
                "data": content,
                "ttl": ttl,
            }
            if rtype == "CNAME":
                # make sure a the data is always a FQDN for CNAMe.
                record["data"] = record["data"].rstrip(".") + "."

            self._post(f"/domains/{self.domain_id}/records", record)
        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        url = f"/domains/{self.domain_id}/records"
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

            for record in payload["domain_records"]:
                processed_record = {
                    "type": record["type"],
                    "name": f"{record['name']}.{self.domain_id}",
                    "ttl": record["ttl"],
                    "content": record["data"],
                    "id": record["id"],
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

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        data = {}
        if rtype:
            data["type"] = rtype
        if name:
            data["name"] = self._relative_name(name)
        if content:
            data["data"] = content

        ttl = self._get_lexicon_option("ttl")
        if ttl:
            data["ttl"] = ttl

        self._put(f"/domains/{self.domain_id}/records/{identifier}", data)

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
            self._delete(f"/domains/{self.domain_id}/records/{record_id}")

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug("delete_record: %s", True)
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
            "Authorization": f"Bearer {self._get_provider_option('auth_token')}",
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
