"""Module provider for DNSPod"""

import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for DNSPod"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["dnsapi.cn"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument("--auth-username", help="specify api id for authentication")
        parser.add_argument("--auth-token", help="specify token for authentication")

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://dnsapi.cn"

    def authenticate(self):
        payload = self._post("/Domain.Info", {"domain": self.domain})

        if payload["status"]["code"] != "1":
            raise AuthenticationError(payload["status"]["message"])

        self.domain_id = payload["domain"]["id"]

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, rtype, name, content):
        record = {
            "domain_id": self.domain_id,
            "sub_domain": self._relative_name(name),
            "record_type": rtype,
            "record_line": "\u9ED8\u8BA4",
            "value": content,
        }
        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        payload = self._post("/Record.Create", record)

        if payload["status"]["code"] not in ["1", "31"]:
            raise Exception(payload["status"]["message"])

        LOGGER.debug("create_record: %s", payload["status"]["code"] == "1")
        return payload["status"]["code"] == "1"

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        payload = self._post("/Record.List", {"domain": self.domain})
        LOGGER.debug("payload: %s", payload)
        records = []
        for record in payload["records"]:
            processed_record = {
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["value"],
                # this id is useless unless your doing record linking.
                # Lets return the original record identifier.
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
            records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        data = {
            "domain_id": self.domain_id,
            "record_id": identifier,
            "sub_domain": self._relative_name(name),
            "record_type": rtype,
            "record_line": "\u9ED8\u8BA4",
            "value": content,
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")
        LOGGER.debug("data: %s", data)
        payload = self._post("/Record.Modify", data)
        LOGGER.debug("payload: %s", payload)
        if payload["status"]["code"] != "1":
            raise Exception(payload["status"]["message"])

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
            self._post(
                "/Record.Remove", {"domain_id": self.domain_id, "record_id": record_id}
            )

            # if payload['status']['code'] != '1':
            #    raise Exception(payload['status']['message'])

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
        if query_params is None:
            query_params = {}
        default_headers = {}
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
