"""Module provider for Cloudflare"""
import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Cloudflare"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["cloudflare.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.description = """
            There are two ways to provide an authentication granting edition to the target CloudFlare DNS zone.
            1 - A Global API key, with --auth-username and --auth-token flags.
            2 - An unscoped API token (permissions Zone:Zone(read) + Zone:DNS(edit) for all zones), with --auth-token flag.
            3 - A scoped API token (permissions Zone:Zone(read) + Zone:DNS(edit) for one zone), with --auth-token and --zone-id flags.
        """
        parser.add_argument(
            "--auth-username",
            help="specify email address for authentication (for Global API key only)",
        )
        parser.add_argument(
            "--auth-token",
            help="specify token for authentication (Global API key or API token)",
        )
        parser.add_argument(
            "--zone-id",
            help="specify the zone id (if set, API token can be scoped to the target zone)",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.cloudflare.com/client/v4"

    def authenticate(self):
        zone_id = self._get_provider_option("zone_id")
        if not zone_id:
            payload = self._get("/zones", {"name": self.domain})

            if not payload["result"]:
                raise AuthenticationError("No domain found")
            if len(payload["result"]) > 1:
                raise AuthenticationError(
                    "Too many domains found. This should not happen"
                )

            self.domain_id = payload["result"][0]["id"]
        else:
            payload = self._get(f"/zones/{zone_id}")

            if not payload["result"]:
                raise AuthenticationError(f"No domain found for Zone ID {zone_id}")

            self.domain_id = zone_id

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, rtype, name, content):
        content, cf_data = self._format_content(rtype, content)
        data = {
            "type": rtype,
            "name": self._full_name(name),
            "content": content,
            "data": cf_data,
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")
        if self._get_lexicon_option("priority"):
            if self._get_lexicon_option("priority").isnumeric():
                data["priority"] = int(self._get_lexicon_option("priority"))

        payload = {"success": True}
        try:
            payload = self._post(f"/zones/{self.domain_id}/dns_records", data)
        except requests.exceptions.HTTPError as err:
            already_exists = next(
                (
                    True
                    for error in err.response.json()["errors"]
                    if error["code"] == 81057
                ),
                False,
            )
            if not already_exists:
                raise

        LOGGER.debug("create_record: %s", payload["success"])
        return payload["success"]

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        filter_obj = {"per_page": 100}
        if rtype:
            filter_obj["type"] = rtype
        if name:
            filter_obj["name"] = self._full_name(name)
        if content:
            filter_obj["content"] = content

        records = []
        while True:
            payload = self._get(f"/zones/{self.domain_id}/dns_records", filter_obj)

            LOGGER.debug("payload: %s", payload)

            for record in payload["result"]:
                processed_record = {
                    "type": record["type"],
                    "name": record["name"],
                    "ttl": record["ttl"],
                    "content": record["content"],
                    "id": record["id"],
                }
                records.append(processed_record)

            pages = payload["result_info"]["total_pages"]
            page = payload["result_info"]["page"]
            if page >= pages:
                break
            filter_obj["page"] = page + 1

        LOGGER.debug("list_records: %s", records)
        LOGGER.debug("Number of records retrieved: %d", len(records))
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

        data = {}
        if rtype:
            data["type"] = rtype
        if name:
            data["name"] = self._full_name(name)
        if content:
            data["content"] = content
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        payload = self._put(f"/zones/{self.domain_id}/dns_records/{identifier}", data)

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

        LOGGER.debug("delete_records: %s", delete_record_id)

        for record_id in delete_record_id:
            self._delete(f"/zones/{self.domain_id}/dns_records/{record_id}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        headers = {"Content-Type": "application/json"}
        if self._get_provider_option("auth_username"):
            headers["X-Auth-Email"] = self._get_provider_option("auth_username")
            headers["X-Auth-Key"] = self._get_provider_option("auth_token")
        else:
            headers[
                "Authorization"
            ] = f"Bearer {self._get_provider_option('auth_token')}"
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

    def _format_content(self, rtype, content):
        """
        Special case handling from some record types that Cloudflare needs
        formatted differently

        Returns new values for the content and data properties to be sent
        on the request
        """
        data = None
        if rtype == "SSHFP":
            # For some reason the CloudFlare API does not let you set content
            # directly when creating an SSHFP record. You need to pass the
            # fields that make up the record seperately, then the API joins
            # them back together
            _fp = content.split(" ")
            data = {"algorithm": _fp[0], "type": _fp[1], "fingerprint": _fp[2]}
            content = None

        return content, data
