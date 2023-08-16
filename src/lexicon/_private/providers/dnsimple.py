"""Module provider for DNS Simple"""
import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for DNS Simple"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["dnsimple.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument("--auth-token", help="specify api token for authentication")
        parser.add_argument(
            "--auth-username", help="specify email address for authentication"
        )
        parser.add_argument(
            "--auth-password", help="specify password for authentication"
        )
        parser.add_argument(
            "--auth-2fa",
            help="specify two-factor auth token (OTP) to use with email/password authentication",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.account_id = None
        self.api_endpoint = (
            self._get_provider_option("api_endpoint") or "https://api.dnsimple.com/v2"
        )

    def authenticate(self):
        payload = self._get("/accounts")

        if not payload[0]["id"]:
            raise AuthenticationError("No account id found")

        for account in payload:
            if account["plan_identifier"] is None:
                logging.warning(
                    "Skipping unconfigured account %s (%d). "
                    "To use this account, you must select a plan.",
                    account["email"],
                    account["id"],
                )
                continue

            dompayload = self._get(
                f"/{account['id']}/domains", query_params={"name_like": self.domain}
            )
            if dompayload and dompayload[0]["id"]:
                self.account_id = account["id"]
                self.domain_id = dompayload[0]["id"]
                break
        else:
            raise AuthenticationError(f"No domain found like {self.domain}")

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing

    def create_record(self, rtype, name, content):
        # check if record already exists
        existing_records = self.list_records(rtype, name, content)
        if len(existing_records) == 1:
            return True

        record = {"type": rtype, "name": self._relative_name(name), "content": content}
        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")
        if self._get_lexicon_option("priority"):
            record["priority"] = self._get_lexicon_option("priority")
        if self._get_provider_option("regions"):
            record["regions"] = self._get_provider_option("regions")

        payload = self._post(f"/{self.account_id}/zones/{self.domain}/records", record)

        LOGGER.debug("create_record: %s", "id" in payload)
        return "id" in payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        filter_query = {}
        if rtype:
            filter_query["type"] = rtype
        if name:
            filter_query["name"] = self._relative_name(name)
        payload = self._get(
            f"/{self.account_id}/zones/{self.domain}/records", query_params=filter_query
        )

        records = []
        for record in payload:
            processed_record = {
                "type": record["type"],
                "name": f"{self.domain}"
                if record["name"] == ""
                else f"{record['name']}.{self.domain}",
                "ttl": record["ttl"],
                "content": record["content"],
                "id": record["id"],
            }
            if record["priority"]:
                processed_record["priority"] = record["priority"]
            records.append(processed_record)

        if content:
            records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        data = {}

        if identifier is None:
            records = self.list_records(rtype, name, content)
            identifiers = [record["id"] for record in records]
        else:
            identifiers = [identifier]

        if name:
            data["name"] = self._relative_name(name)
        if content:
            data["content"] = content
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")
        if self._get_lexicon_option("priority"):
            data["priority"] = self._get_lexicon_option("priority")
        if self._get_provider_option("regions"):
            data["regions"] = self._get_provider_option("regions")

        for one_identifier in identifiers:
            self._patch(
                f"/{self.account_id}/zones/{self.domain}/records/{one_identifier}", data
            )
            LOGGER.debug("update_record: %s", one_identifier)

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
            self._delete(f"/{self.account_id}/zones/{self.domain}/records/{record_id}")

        # is always True at this point; if a non 2xx response is returned, an error is raised.
        LOGGER.debug("delete_record: True")
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
        }
        default_auth = None

        if self._get_provider_option("auth_token"):
            default_headers[
                "Authorization"
            ] = f"Bearer {self._get_provider_option('auth_token')}"
        elif self._get_provider_option("auth_username") and self._get_provider_option(
            "auth_password"
        ):
            default_auth = (
                self._get_provider_option("auth_username"),
                self._get_provider_option("auth_password"),
            )
            if self._get_provider_option("auth_2fa"):
                default_headers["X-Dnsimple-OTP"] = self._get_provider_option(
                    "auth_2fa"
                )
        else:
            raise Exception("No valid authentication mechanism found")

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
            auth=default_auth,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if response.text and response.json()["data"] is None:
            raise Exception("No data returned")

        return response.json()["data"] if response.text else None

    def _patch(self, url="/", data=None, query_params=None):
        return self._request("PATCH", url, data=data, query_params=query_params)
