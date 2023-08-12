"""Module provider for UKFast's SafeDNS"""
import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider SafeDNS implementation of Lexicon Provider interface."""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["ukfast.net"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.description = """
            SafeDNS provider requires an API key in all interactions.
            You can generate one for your account on the following URL:
            https://my.ukfast.co.uk/applications/index.php"""
        parser.add_argument(
            "--auth-token", help="specify the API key to authenticate with"
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.ukfast.io/safedns/v1"

    def authenticate(self):
        try:
            self._get(f"/zones/{self.domain}")
            self.domain_id = self.domain
        except requests.exceptions.HTTPError as err:
            if err.response.status_code == 404:
                raise AuthenticationError("No domain found")
            raise err

    def cleanup(self) -> None:
        pass

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    def list_records(self, rtype=None, name=None, content=None):
        url = f"/zones/{self.domain_id}/records"
        records = []
        payload = {}

        # Handle pagination and iteratively collect all records
        next_url = url
        while next_url is not None:
            payload = self._get(next_url)
            if (
                "meta" in payload
                and "pagination" in payload["meta"]
                and "links" in payload["meta"]["pagination"]
                and "next" in payload["meta"]["pagination"]["links"]
            ):
                next_url = payload["meta"]["pagination"]["links"]["next"]
            else:
                next_url = None

            # Assign the returned attributes to the keys that lexicon expects
            for record in payload["data"]:
                record = self._clean_TXT_record(record)
                processed_record = {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "content": record["content"],
                    "updated_at": record["updated_at"],
                    "ttl": record["ttl"],
                    "priority": record["priority"],
                }
                records.append(processed_record)

        # This is filtering logic to return only the record which matches what has
        # been passed in to the method
        if rtype:
            records = [record for record in records if record["type"] == rtype]
        if name:
            records = [
                record
                for record in records
                # DNS should not be case-sensitive, so perform lower-case comparison
                if record["name"].lower() == self._full_name(name).lower()
            ]
        if content:
            records = [
                record
                for record in records
                if record["content"].lower() == content.lower()
            ]

        LOGGER.debug("list_records: %s", records)
        return records

    def create_record(self, rtype, name, content):
        # Check whether the record already exists with the same  rtype, name & content.
        # If so, claim to have added the record, but dont't do anything.
        records = self.list_records(rtype, name, content)
        if records:
            LOGGER.debug(
                "create_record: (ignored, duplicate record): %s", records[0]["id"]
            )
            return True

        # Make sure TXT records are wrapped in quotes
        if content:
            content = self._add_quotes(rtype, content)

        data = {"name": self._full_name(name), "type": rtype, "content": content}

        self._post(f"/zones/{self.domain}/records", data)
        LOGGER.debug("create_record: %s", True)
        return True

    def update_record(self, identifier, rtype=None, name=None, content=None):
        # Make sure the update won't cause a duplicate entry. If it will, fail silently
        records = self.list_records(rtype, name, content)

        if not identifier:
            records = self.list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            elif len(records) > 1:
                identifier = records[0]["id"]
                LOGGER.warning(
                    "Warning, multiple records found for given parameters, "
                    "only first one will be updated: %s",
                    records,
                )
            else:
                raise Exception("Record identifier could not be found")

        # Make sure TXT records are wrapped in quotes
        if content:
            content = self._add_quotes(rtype, content)

        data = {}
        if name:
            data["name"] = self._full_name(name)
        if rtype:
            data["type"] = rtype
        if content:
            data["content"] = content

        self._patch(f"/zones/{self.domain}/records/{identifier}", data)

        LOGGER.debug("update_record: %s", True)
        return True

    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_ids = []

        # If we've not been given an identifier, search for matching records.
        # NOTE, this could cause multiple records to be removed.
        if not identifier:
            records = self.list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_ids)

        for delete_record_id in delete_record_ids:
            self._delete(f"/zones/{self.domain}/records/{delete_record_id}")

        LOGGER.debug("delete_record: %s", True)
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"{self._get_provider_option('auth_token')}",
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

        # Sort this out to work properly, writing errors to the correct place
        if "content" in response:
            resp = json.loads(response.content)
            if "errors" in resp:
                for error in resp["errors"]:
                    print("ERROR: " + error["detail"])

        # If the request fails for any reason, throw an error.
        response.raise_for_status()

        # There is no JSON returned when calling with DELETE
        if action != "DELETE":
            return response.json()

        return True

    # The content of TXT entries must be quoted. This static method ensures that.
    @staticmethod
    def _add_quotes(rtype, content):
        if rtype == "TXT":
            if not content.startswith('"') and not content.endswith('"'):
                return f'"{content}"'
        return content
