"""Module provider for Linode"""
import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Linode"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return []

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument("--auth-token", help="specify api key for authentication")

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.linode.com/api/"

    def authenticate(self):
        self.domain_id = None
        payload = self._get("domain.list")
        for domain in payload["DATA"]:
            if domain["DOMAIN"].lower() == self.domain.lower():
                self.domain_id = domain["DOMAINID"]
                break
        else:
            raise AuthenticationError("Domain not found")

    def cleanup(self) -> None:
        pass

    def create_record(self, rtype, name, content):
        if not self.list_records(rtype, name, content):
            self._get(
                "domain.resource.create",
                query_params={
                    "DomainID": self.domain_id,
                    "Name": self._relative_name(name).lower(),
                    "Type": rtype,
                    "Target": content,
                    "TTL_sec": 0,
                },
            )

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        payload = self._get(
            "domain.resource.list", query_params={"DomainID": self.domain_id}
        )
        resource_list = payload["DATA"]
        if rtype:
            resource_list = [
                resource for resource in resource_list if resource["TYPE"] == rtype
            ]
        if name:
            cmp_name = self._relative_name(name).lower()
            resource_list = [
                resource
                for resource in resource_list
                if resource["NAME"].lower() == cmp_name
            ]
        if content:
            resource_list = [
                resource for resource in resource_list if resource["TARGET"] == content
            ]

        processed_records = []
        for resource in resource_list:
            processed_records.append(
                {
                    "id": resource["RESOURCEID"],
                    "type": resource["TYPE"],
                    "name": self._full_name(resource["NAME"]).lower(),
                    "ttl": resource["TTL_SEC"],
                    "content": resource["TARGET"],
                }
            )
        LOGGER.debug("list_records: %s", processed_records)
        return processed_records

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier:
            resources = self.list_records(rtype, name, None)
            identifier = resources[0]["id"] if resources else None

        LOGGER.debug("update_record: %s", identifier)

        self._get(
            "domain.resource.update",
            query_params={
                "DomainID": self.domain_id,
                "ResourceID": identifier,
                "Name": self._relative_name(name).lower() if name else None,
                "Type": rtype if rtype else None,
                "Target": content if content else None,
            },
        )

        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_resource_id = []
        if not identifier:
            resources = self.list_records(rtype, name, content)
            delete_resource_id = [resource["id"] for resource in resources]
        else:
            delete_resource_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_resource_id)

        for resource_id in delete_resource_id:
            self._get(
                "domain.resource.delete",
                query_params={"DomainID": self.domain_id, "ResourceID": resource_id},
            )

        return True

    # Helpers
    def _request(self, action="GET", url="", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        query_params["api_key"] = self._get_provider_option("auth_token")
        query_params["resultFormat"] = "JSON"
        query_params["api_action"] = url

        response = requests.request(
            action,
            self.api_endpoint,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if action == "DELETE":
            return ""
        result = response.json()
        if result["ERRORARRAY"]:
            raise Exception(f"Linode api error: {result['ERRORARRAY']}")
        return result
