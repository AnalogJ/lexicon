"""Module provider for CloudXNS"""
import hashlib
import json
import logging
import time
from argparse import ArgumentParser
from typing import List
from urllib.parse import urlencode

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for CloudXNS"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["cloudxns.net"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-username", help="specify API-KEY for authentication"
        )
        parser.add_argument(
            "--auth-token", help="specify SECRET-KEY for authentication"
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://www.cloudxns.net/api2"

    def authenticate(self):
        payload = self._get("/domain")
        for record in payload["data"]:
            if record["domain"] == self.domain + ".":
                self.domain_id = record["id"]
                break
        else:
            raise AuthenticationError("No domain found")

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, rtype, name, content):
        record = {
            "domain_id": self.domain_id,
            "host": self._relative_name(name),
            "value": content,
            "type": rtype,
            "line_id": 1,
        }
        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        try:
            self._post("/record", record)
        except requests.exceptions.HTTPError as err:
            already_exists = err.response.json()["code"] == 34
            if not already_exists:
                raise

        # CloudXNS will return bad HTTP Status when error, will throw at
        # r.raise_for_status() in _request()
        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        payload = self._get(
            "/record/" + self.domain_id, {"host_id": 0, "offset": 0, "row_num": 2000}
        )
        records = []
        for record in payload["data"]:
            processed_record = {
                "type": record["type"],
                "name": self._full_name(record["host"]),
                "ttl": record["ttl"],
                "content": record["value"],
                # this id is useless unless your doing record linking. Lets return the
                # original record identifier.
                "id": record["record_id"],
            }
            if processed_record["type"] == "TXT":
                processed_record["content"] = processed_record["content"].replace(
                    '"', ""
                )
                # CloudXNS will add quotes automaticly for TXT records,
                # https://www.cloudxns.net/Support/detail/id/114.html
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
        if not identifier:
            records = self.list_records(name=name)
            if len(records) == 1:
                identifier = records[0]["id"]
            else:
                raise Exception("Record identifier could not be found.")

        data = {
            "domain_id": self.domain_id,
            "host": self._relative_name(name),
            "value": content,
            "type": rtype,
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        self._put("/record/" + identifier, data)

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
            self._delete("/record/" + record_id + "/" + self.domain_id)

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        data["login_token"] = (
            self._get_provider_option("auth_username")
            + ","
            + self._get_provider_option("auth_token")
        )
        data["format"] = "json"
        if query_params:
            query_string = "?" + urlencode(query_params)
        else:
            query_string = ""
            query_params = {}
        if data:
            data = json.dumps(data)
        else:
            data = ""
        date = time.strftime("%a %b %d %H:%M:%S %Y", time.localtime())
        default_headers = {
            "API-KEY": self._get_provider_option("auth_username"),
            "API-REQUEST-DATE": date,
            "API-HMAC": hashlib.md5(
                f"{self._get_provider_option('auth_username')}{self.api_endpoint}{url}{query_string}{data}{date}{self._get_provider_option('auth_token')}".encode(
                    "utf-8"
                )
            ).hexdigest(),
            "API-FORMAT": "json",
        }
        default_auth = None
        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=data,
            headers=default_headers,
            auth=default_auth,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()
