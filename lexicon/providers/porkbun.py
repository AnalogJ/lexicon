import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["porkbun.com"]


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.description = """
        To authenticate with Porkbun, you need both an API key and a
        secret API key. These can be created at porkbun.com/account/api .
    """

    subparser.add_argument("--auth-key", help="specify API key for authentication")
    subparser.add_argument(
        "--auth-secret", help="specify secret API key for authentication"
    )


class Provider(BaseProvider):
    """Provider class for Porkbun"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = "https://porkbun.com/api/json/v3"
        self._api_key = self._get_provider_option("auth_key")
        self._secret_api_key = self._get_provider_option("auth_secret")
        self._auth_data = {
            "apikey": self._api_key,
            "secretapikey": self._secret_api_key,
        }

        self.domain = self._get_lexicon_option("domain")

    def _authenticate(self):
        # more of a test that the authentication works
        response = self._post("/ping")

        if response["status"] != "SUCCESS":
            raise AuthenticationError("Incorrect API keys")
        self.domain_id = self.domain
        self._list_records()

    def _create_record(self, rtype, name, content):
        active_records = self._list_records(rtype, name, content)
        # if the record already exists: early exit, return success
        if active_records:
            LOGGER.debug("create_record: record already exists")
            return True

        data = {
            "type": rtype,
            "content": content,
            "name": self._relative_name(name),
        }

        if self._get_lexicon_option("priority"):
            data["prio"] = self._get_lexicon_option("priority")

        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        response = self._post(f"/dns/create/{self.domain}", data)

        LOGGER.debug(f"create_record: {response}")
        return response["status"] == "SUCCESS"

    def _list_records(self, rtype=None, name=None, content=None):
        # porkbun has some weird behavior on the retrieveByNameType endpoint
        # related to how it handles subdomains.
        # so we ignore it and filter locally instead
        records = self._post(f"/dns/retrieve/{self.domain}")

        if records["status"] != "SUCCESS":
            raise requests.exceptions.HTTPError(records)

        records = records["records"]

        records = self._format_records(records)

        # filter for content if it was provided
        if content is not None:
            records = [x for x in records if x["content"] == content]

        # filter for name if it was provided
        if name is not None:
            records = [x for x in records if x["name"] == self._full_name(name)]

        # filter for rtype if it was provided
        if rtype is not None:
            records = [x for x in records if x["type"] == rtype]

        LOGGER.debug(f"list_records: {records}")
        LOGGER.debug(f"Number of records retrieved: {len(records)}")
        return records

    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier is None:
            records = self._list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            elif len(records) == 0:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )

        endpoint = f"/dns/edit/{self.domain}/{identifier}"

        data = {"name": self._relative_name(name), "type": rtype, "content": content}

        # if set to 0, then this will automatically get set to 300
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        if self._get_lexicon_option("priority"):
            data["prio"] = self._get_lexicon_option("priority")

        result = self._post(endpoint, data)

        LOGGER.debug(f"update_record: {result}")
        return result["status"] == "SUCCESS"

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier is None:
            records = self._list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids = [identifier]

        LOGGER.debug(f"deleting records: {delete_record_ids}")

        for record_id in delete_record_ids:
            self._post(f"/dns/delete/{self.domain}/{record_id}")

        LOGGER.debug("delete_record: success")
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        headers = {"Content-Type": "application/json"}

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps({**data, **self._auth_data}),
            headers=headers,
        )

        response.raise_for_status()
        return response.json()

    def _format_records(self, records):
        for record in records:
            record["name"] = self._full_name(record["name"])
            if "prio" in record:
                record["options"] = {"mx": {"priority": record["prio"]}}
                del record["prio"]
        return records
