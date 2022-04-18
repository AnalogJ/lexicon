"""Module provider for Hover"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["hover.com"]


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )


class Provider(BaseProvider):
    """Provider class for Hover"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://www.hover.com/api"
        self.cookies = {}

    def _authenticate(self):
        # Getting required cookies "hover_session" and "hoverauth"
        response = requests.get("https://www.hover.com/signin")
        self.cookies["hover_session"] = response.cookies["hover_session"]

        payload = {
            "username": self._get_provider_option("auth_username"),
            "password": self._get_provider_option("auth_password"),
        }
        response = requests.post(
            "https://www.hover.com/api/login/", json=payload, cookies=self.cookies
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
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get(f"/domains/{self.domain_id}/dns")

        # payload['domains'] should be a list of len 1
        try:
            raw_records = payload["domains"][0]["entries"]
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

    def _create_record(self, rtype, name, content):
        name = self._relative_name(name)
        records = self._list_records(rtype, name, content)
        if records:
            LOGGER.debug("not creating duplicate record: %s", records[0])
            return True

        record = {"name": name, "type": rtype, "content": content}
        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        LOGGER.debug("create_record: %s", record)
        payload = self._post(f"/domains/{self.domain_id}/dns", record)
        return payload["succeeded"]

    # Update a record. Hover cannot update name so we delete and recreate.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier:
            records = self._list_records()
            records = [r for r in records if r["id"] == identifier]
        else:
            records = self._list_records(rtype, name, None)

        if not records:
            raise Exception("Record not found")
        if len(records) > 1:
            raise Exception("Record not unique")
        orig_record = records[0]
        orig_id = orig_record["id"]

        new_rtype = rtype if rtype else orig_record["type"]
        new_name = name if name else orig_record["name"]
        new_content = content if content else orig_record["content"]

        self._delete_record(orig_id)
        return self._create_record(new_rtype, new_name, new_content)

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_ids)

        for record_id in delete_record_ids:
            self._delete(f"/dns/{record_id}")
            LOGGER.debug("delete_record: %s", record_id)
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
