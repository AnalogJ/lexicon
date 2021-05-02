"""Module provider for Infomaniak"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

ENDPOINT = "https://api.infomaniak.com"

NAMESERVER_DOMAINS = ["infomaniak.com"]


def provider_parser(subparser):
    """Generate provider parser for Infomaniak"""
    subparser.description = """
        Infomaniak Provider requires a token with domain scope.
        It can be generated for your Infomaniak account on the following URL:
        https://manager.infomaniak.com/v3/infomaniak-api"""

    subparser.add_argument("--auth-token", help="specify the token")


class Provider(BaseProvider):
    """Provider class for Infomaniak"""

    def __init__(self, config):
        super(Provider, self).__init__(config)

        # Handling missing required parameters
        if not self._get_provider_option("auth_token"):
            raise Exception("Error, token is not defined")

        # Construct DNS Infomaniak environment
        self.domain_id = None
        self.endpoint_api = ENDPOINT
        self.session = None

    def _authenticate(self):
        domains = self._get(
            "/1/product", {"service_name": "domain", "customer_name": self.domain}
        )

        LOGGER.debug("found domains %s", domains)

        for domain in domains["data"]:
            if domain["customer_name"] == self.domain:
                self.domain_id = domain["id"]
                break
        else:
            raise AuthenticationError(f"Domain {self.domain} not found")

    def _create_record(self, rtype, name, content):
        ttl = self._get_lexicon_option("ttl")

        records = list(
            filter(
                lambda x: x["content"] == content
                and x["type"] == rtype
                and self._relative_name(x["name"]) == self._relative_name(name),
                self._list_records(rtype, name, content),
            )
        )

        if len(records) > 0:
            LOGGER.debug(
                "create_record (ignored, duplicate): %s %s %s", rtype, name, content
            )
            return True

        data = {
            "type": rtype,
            "source": self._relative_name(name),
            "target": content,
        }

        if ttl:
            data["ttl"] = ttl

        result = self._post(f"/1/domain/{self.domain_id}/dns/record", data)

        LOGGER.debug("create_record: %s", result["data"])

        return True

    def _list_records(self, rtype=None, name=None, content=None):
        records = []

        record_data = self._get(f"/1/domain/{self.domain_id}/dns/record")

        for record in record_data["data"]:
            records.append(
                {
                    "type": record["type"],
                    "name": record["source_idn"],
                    "ttl": record["ttl"],
                    "content": record["target_idn"],
                    "id": record["id"],
                }
            )

        if rtype:
            records = [record for record in records if record["type"] == rtype]

        if name:
            records = [
                record
                for record in records
                if record["name"].lower() == self._full_name(name.lower())
            ]

        if content:
            records = [
                record
                for record in records
                if record["content"].lower() == content.lower()
            ]

        LOGGER.debug("list_records: %s", records)

        return records

    def _get_record(self, identifier):
        record_data = self._get(f"/1/domain/{self.domain_id}/dns/record/{identifier}")

        record = {
            "type": record_data["data"]["type"],
            "name": record_data["data"]["source_idn"],
            "ttl": record_data["data"]["ttl"],
            "content": record_data["data"]["target_idn"],
            "id": record_data["data"]["id"],
        }

        LOGGER.debug("get_record: %s", record)

        return record

    def _update_record(self, identifier, rtype=None, name=None, content=None):

        records = self._list_records(rtype, name)

        if not identifier:
            if len(records) == 1:
                identifier = records[0]["id"]
                record = records[0]
            elif len(records) > 1:
                raise Exception("Several record identifiers match the request")
            else:
                raise Exception("Record identifier could not be found")
        else:
            record = self._get_record(identifier)

        data = {"ttl": record["ttl"]}
        if name:
            data["source"] = self._relative_name(name)
        if content:
            data["target"] = content

        self._put(f"/1/domain/{self.domain_id}/dns/record/{identifier}", data)

        LOGGER.debug("update_record: %s", identifier)

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)

        for record_id in delete_record_id:
            self._delete(f"/1/domain/{self.domain_id}/dns/record/{record_id}")

        LOGGER.debug("delete_record: %s", True)

        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        headers = {}
        target = self.endpoint_api + url
        body = ""

        if data is not None:
            headers["Content-type"] = "application/json"
            body = json.dumps(data)

        headers["Authorization"] = f"Bearer {self._get_provider_option('auth_token')}"

        result = requests.request(
            method=action, url=target, params=query_params, data=body, headers=headers
        )
        result.raise_for_status()

        json_result = result.json()

        if json_result["result"] != "success":
            raise Exception("API didn't return success status")

        return json_result
