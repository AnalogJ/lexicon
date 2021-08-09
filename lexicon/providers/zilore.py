"""Implement a provider for Zilore (https://zilore.com)"""
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["zilore.net"]


def provider_parser(subparser):
    """Construct a subparser for Zilore provider"""
    subparser.description = """
    Zilore API requires an API key that can be found in your Zilore profile, at the API tab.
    The API access is available only for paid plans.
    """
    subparser.add_argument("--auth-key", help="specify the Zilore API key to use")


class Provider(BaseProvider):
    """
    Construct the Zilore provider

    Zilore API is very clean and well constructed. All features required to make direct
    CRUD operations are present, including update, and record ids. The filters to list
    records given in the specification seems to not work, but can be easily done on Lexicon
    side using list comprehension on the provided arguments on _list_records.

    Authentication is done by passing the API key specific to a user in the X-Auth-Key header.
    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None

    def _authenticate(self):
        result = self._get("/domains")

        target_domain = [
            item for item in result["response"] if item["domain_name"] == self.domain
        ]

        if not target_domain:
            raise AuthenticationError(
                f"Domain {self.domain} is not available on this account"
            )

        self.domain_id = target_domain[0]["domain_id"]

    def _list_records(self, rtype=None, name=None, content=None):
        result = self._get(f"/domains/{self.domain}/records", {})

        records = [
            self._clean_TXT_record(
                {
                    "id": item["record_id"],
                    "type": item["record_type"],
                    "name": self._full_name(item["record_name"]),
                    "content": item["record_value"],
                    "ttl": item["record_ttl"],
                }
            )
            for item in result["response"]
        ]

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

    def _create_record(self, rtype, name, content):
        if not rtype or not name or not content:
            raise Exception(
                "Error, rtype, name and content are mandatory to create a record."
            )

        records = self._list_records(rtype, name, content)

        if records:
            LOGGER.debug("not creating a duplicate record: %s", records[0])
            return True

        record = {
            "record_type": rtype,
            "record_name": self._full_name(name),
            "record_value": content if rtype != "TXT" else f'"{content}"',
        }

        if self._get_lexicon_option("ttl"):
            record["record_ttl"] = self._get_lexicon_option("ttl")

        result = self._post(f"/domains/{self.domain}/records", query_params=record)

        LOGGER.debug("create_record: %s", result["response"]["record_id"])

        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier and (not rtype and not name):
            raise Exception("Error, identifier or rtype+name parameters are required.")

        if identifier:
            records = self._list_records()
            records_to_update = [
                record for record in records if record["id"] == identifier
            ]
        else:
            records_to_update = self._list_records(rtype=rtype, name=name)

        if not records_to_update:
            raise Exception("Error, could not find a record matching the request.")

        if len(records_to_update) > 1:
            LOGGER.warning(
                "Warning, multiple records found for given parameters, "
                "only first one will be updated: %s",
                records_to_update,
            )

        record = records_to_update[0]
        update = {
            "record_type": rtype if rtype else record["type"],
            "record_name": self._full_name(name) if name else record["name"],
            "record_ttl": self._get_lexicon_option("ttl")
            if self._get_lexicon_option("ttl")
            else record["ttl"],
        }

        if content:
            update["record_value"] = content if rtype != "TXT" else f'"{content}"'

        result = self._put(
            f"/domains/{self.domain}/records/{record['id']}", query_params=update
        )

        LOGGER.debug("update_record: %s", result["response"]["record_id"])

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            records = self._list_records()
            records_to_delete = [
                record for record in records if record["id"] == identifier
            ]
        else:
            records_to_delete = self._list_records(
                rtype=rtype, name=name, content=content
            )

        if not records_to_delete:
            raise Exception("Error, could not find a record matching the request.")

        for record in records_to_delete:
            self._delete(
                f"/domains/{self.domain}/records",
                query_params={"record_id": record["id"]},
            )

            LOGGER.debug("delete_record: %s %s %s %s", identifier, rtype, name, content)

        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        response = requests.request(
            action,
            f"https://api.zilore.com/dns/v1{url}",
            params=query_params,
            json=data,
            headers={"X-Auth-Key": self._get_provider_option("auth_key")},
        )

        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as error:
            LOGGER.error("Content of error response:")
            LOGGER.error(response.json())
            raise error

        return response.json()
