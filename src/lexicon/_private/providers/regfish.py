"""Module provider for Regfish"""

import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Regfish"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["regfish-ns.net"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-api-key",
            help="specify API key for authentication",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.regfish.de"

    def authenticate(self):
        payload = self._get(f"/dns/{self.domain}/rr")
        if not payload["success"]:
            raise AuthenticationError("No domain found")
        self.domain_id = 0

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, rtype, name, content):
        content = self._format_content(rtype, content)
        data = {
            "type": rtype,
            "name": self._fqdn_name(name),
            "data": content,
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")
        if self._get_lexicon_option("priority"):
            if self._get_lexicon_option("priority").isnumeric():
                data["priority"] = int(self._get_lexicon_option("priority"))

        payload = {"success": True}
        try:
            payload = self._post("/dns/rr", data)
        except requests.exceptions.HTTPError as err:
            json_res = err.response.json()
            if (
                not json_res["code"] if "code" in json_res else 0 != 15003
            ):  # ResourceRecordAlreadyExists
                raise

        if payload["code"] if "code" in payload else 0 != 0:
            return False

        LOGGER.debug("create_record: %s", payload["success"])
        return payload["success"]

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        records = []
        payload = self._get(f"/dns/{self.domain}/rr")

        LOGGER.debug("payload: %s", payload)

        for record in payload["response"]:
            processed_record = {
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["data"],
                "id": record["id"],
            }
            records.append(processed_record)

        # Apply filters on rtype, name, and content if they are provided
        if rtype or name or content:
            records = [
                record
                for record in records
                if (not rtype or record["type"] == rtype)
                and (not name or record["name"] == self._full_name(name))
                and (
                    not content
                    or record["content"] == self._format_content(rtype, content)
                )
            ]

        LOGGER.debug("list_records after filtering: %s", records)
        LOGGER.debug("Number of records retrieved after filtering: %d", len(records))
        return records

    # Create or update a record.
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

        content = self._format_content(rtype, content)
        data = {}
        if rtype:
            data["type"] = rtype
        if name:
            data["name"] = self._fqdn_name(name)
        if content:
            data["data"] = content
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        payload = self._patch(f"/dns/rr/{identifier}", data)

        LOGGER.debug("update_record: %s", payload["success"])
        return payload["success"]

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self.list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        # Check if there are records to delete
        if not delete_record_id:
            # No records found to delete, raise an error or return False
            raise Exception(f"No matching records found to delete {identifier}")

        for record_id in delete_record_id:
            self._delete(f"/dns/rr/{record_id}")

        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        headers = {"Content-Type": "application/json", "Acccept": "application/json"}
        headers["x-api-key"] = self._get_provider_option("auth_api_key")
        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data) if data else None,
            headers=headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    def _format_content(self, rtype, content):
        """
        Special case handling from some record types that Regfish needs
        formatted differently

        Returns new values for the content and data properties to be sent
        on the request
        """
        if rtype == "CNAME":
            content = content.rstrip(".") + "."

        return content
