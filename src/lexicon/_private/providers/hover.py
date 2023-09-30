"""Module provider for Hover"""
import json
import logging
import re
from argparse import ArgumentParser
from typing import List

import pyotp
import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for Hover"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["hover.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-username", help="specify username for authentication"
        )
        parser.add_argument(
            "--auth-password", help="specify password for authentication"
        )
        parser.add_argument(
            "--auth-totp-secret",
            help="specify base32-encoded shared secret to generate an OTP for authentication",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://www.hover.com/api"
        self.cookies = {}
        shared_secret = re.sub(
            r"\s*", "", self._get_provider_option("auth_totp_secret") or ""
        )
        self.totp = pyotp.TOTP(shared_secret)

    def authenticate(self) -> None:
        # Getting required cookies "hover_session" and "hoverauth"
        response = requests.get("https://www.hover.com/signin")
        self.cookies["hover_session"] = response.cookies["hover_session"]

        # Part one, login credentials
        payload = {
            "username": self._get_provider_option("auth_username"),
            "password": self._get_provider_option("auth_password"),
        }
        response = requests.post(
            "https://www.hover.com/signin/auth.json", json=payload, cookies=self.cookies
        )
        response.raise_for_status()

        # Part two, 2fa
        payload = {"code": self.totp.now()}
        response = requests.post(
            "https://www.hover.com/signin/auth2.json",
            json=payload,
            cookies=self.cookies,
        )
        response.raise_for_status()

        if "hoverauth" not in response.cookies:
            raise Exception("Unexpected auth response")
        self.cookies["hoverauth"] = response.cookies["hoverauth"]

        # Make sure domain exists
        # domain is stored in self.domain from BaseProvider

        domains = self._list_domains()
        for domain in domains:
            if domain["name"] == self.domain:
                self.domain_id = domain["id"]
                break
        else:
            raise AuthenticationError(f"Domain {self.domain} not found")

    def cleanup(self) -> None:
        pass

    def _list_domains(self):
        response = self._get("/domains")

        domains = []
        for domain in response["domains"]:
            processed_domain = {
                "name": domain["domain_name"],
                "id": domain["id"],
                "active": (domain["status"] == "active"),
            }
            domains.append(processed_domain)

        LOGGER.debug("list_domains: %s", domains)
        return domains

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        payload = self._get(f"/control_panel/dns/{self.domain}")

        # payload['domains'] should be a list of len 1
        try:
            raw_records = payload["domain"]["dns"]
        except (KeyError, IndexError):
            raise Exception("Unexpected response")

        processed_records = []
        for record in raw_records:
            processed_record = {
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["content"],
                "id": record["id"],
            }
            processed_records.append(processed_record)

        if rtype:
            processed_records = [
                record for record in processed_records if record["type"] == rtype
            ]
        if name:
            name = self._relative_name(name)
            processed_records = [
                record for record in processed_records if name in record["name"]
            ]
        if content:
            processed_records = [
                record
                for record in processed_records
                if record["content"].lower() == content.lower()
            ]

        LOGGER.debug("list_records: %s", processed_records)
        return processed_records

    def create_record(self, rtype, name, content):
        name = self._relative_name(name)
        records = self.list_records(rtype, name, content)
        if records:
            LOGGER.debug("not creating duplicate record: %s", records[0])
            return True

        record = {"name": name, "type": rtype, "content": content}
        if self._get_lexicon_option("ttl"):
            record["ttl"] = str(self._get_lexicon_option("ttl"))

        LOGGER.debug("create_record: %s", record)
        payload = {"id": f"domain-{self.domain}", "dns_record": record}
        response = self._post("/control_panel/dns", payload)

        return response["succeeded"]

    # Update a record. Hover cannot update name so we delete and recreate.
    def update_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            records = self.list_records()
            records = [r for r in records if r["id"] == identifier]
        else:
            records = self.list_records(rtype, name, None)

        if not records:
            raise Exception("Record not found")
        if len(records) > 1:
            raise Exception("Record not unique")
        orig_record = records[0]
        orig_id = orig_record["id"]

        new_rtype = rtype if rtype else orig_record["type"]
        new_name = name if name else orig_record["name"]
        new_content = content if content else orig_record["content"]

        self.delete_record(orig_id)
        return self.create_record(new_rtype, new_name, new_content)

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self.list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_ids)
        payload = {
            "domains": [
                {"id": f"domain-{self.domain}", "dns_records": delete_record_ids}
            ]
        }
        self._request("DELETE", "/control_panel/dns", payload)

        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            cookies=self.cookies,
            headers={"Content-Type": "application/json"},
        )

        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:  # response is not json
            raise Exception("Did not get JSON response.")
