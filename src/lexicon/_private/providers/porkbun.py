import json
import logging
from argparse import ArgumentParser
from typing import List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Porkbun"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["porkbun.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.description = """
            To authenticate with Porkbun, you need both an API key and a
            secret API key. These can be created at porkbun.com/account/api .
        """

        parser.add_argument("--auth-key", help="specify API key for authentication")
        parser.add_argument(
            "--auth-secret", help="specify secret API key for authentication"
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = "https://api.porkbun.com/api/json/v3"
        self._api_key = self._get_provider_option("auth_key")
        self._secret_api_key = self._get_provider_option("auth_secret")
        self._auth_data = {
            "apikey": self._api_key,
            "secretapikey": self._secret_api_key,
        }

        self.domain = self._get_lexicon_option("domain")

    def authenticate(self):
        # more of a test that the authentication works
        response = self._post("/ping")

        if response["status"] != "SUCCESS":
            raise AuthenticationError("Incorrect API keys")
        self.domain_id = self.domain
        self.list_records()

    def cleanup(self) -> None:
        pass

    def create_record(self, rtype, name, content):
        active_records = self.list_records(rtype, name, content)
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

    def list_records(self, rtype=None, name=None, content=None):
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

    def update_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier is None:
            records = self.list_records(rtype, name)
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

    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier is None:
            records = self.list_records(rtype, name, content)
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

        # Porkbun has rate limits, but they don't seem to be officially documented anywhere.
        # This comment includes a reply from Porkbun support providing some details on the limits:
        # https://github.com/cullenmcdermott/terraform-provider-porkbun/issues/23#issuecomment-1366859999
        #
        # "About 60 / minute or 2 / second. There are some bursting capabilities up to 5 / second.
        # The best bet would be to keep things to 1 / second if there are constant commands being
        # issued and to wait / resend if a threshold is reached."
        with requests.Session() as session:
            # This Retry configuration attempts to follow the above advice. If requests fail with a 503,
            # we will attempt retries with the following delays between attempts:
            # 0s, 1s, 2s, 4s, 8s, 16s, 32s (for a total of ~63 seconds from the first failure)
            # If we still get a 503 after waiting that long, something else is probably wrong.
            session_retries = Retry(
                total=7,
                backoff_factor=0.5,
                status_forcelist=[503],  # indicates we hit the rate limit
                allowed_methods=frozenset({"POST"}),  # POST is all we ever do here
            )
            session_adapter = HTTPAdapter(max_retries=session_retries)
            session.mount("https://", session_adapter)
            response = session.request(
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
