"""Module provider for Vercel"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["vercel-dns.com"]


def provider_parser(subparser):
    """Configure provider parser for Vercel"""
    subparser.description = """
        Vercel provider requires a token to access its API.
        You can generate one for your account on the following URL:
        https://vercel.com/account/tokens"""
    subparser.add_argument("--auth-token", help="specify your API token")


class Provider(BaseProvider):
    """
    Implements the DNS Vercel provider.
    The API is quite simple: you can list all records, add one record or delete one record.
        - list is pretty straightforward: we get all records then filter for given parameters,
        - add uses directly the API to add a new record without any added complexity,
        - delete uses list + delete: we get the list of all records,
          filter on the given parameters and delete record by id,
        - update uses list + delete + add: we get the list of all records,
          find record for given identifier, then insert a new record and delete the old record.
    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.vercel.com"

    def _authenticate(self):
        result = self._get(f"/v5/domains/{self.domain}")

        identifier = result.get("domain", {}).get("id")

        if not identifier:
            raise AuthenticationError(f"Error, domain {self.domain} not found")

        self.domain_id = identifier

    def _list_records(self, rtype=None, name=None, content=None):
        result = self._get(f"/v4/domains/{self.domain}/records")

        raw_records = result["records"]
        if rtype:
            raw_records = [
                raw_record for raw_record in raw_records if raw_record["type"] == rtype
            ]
        if name:
            raw_records = [
                raw_record
                for raw_record in raw_records
                if raw_record["name"] == self._relative_name(name)
            ]
        if content:
            raw_records = [
                raw_record
                for raw_record in raw_records
                if raw_record["value"] == content
            ]

        records = []
        for raw_record in raw_records:
            records.append(
                {
                    "id": raw_record["id"],
                    "type": raw_record["type"],
                    "name": self._full_name(raw_record["name"]),
                    "content": raw_record["value"],
                    "ttl": raw_record["ttl"],
                }
            )

        LOGGER.debug("list_records: %s", records)

        return records

    def _create_record(self, rtype, name, content):
        # We ignore creation if a record already exists for given rtype/name/content
        records = self._list_records(rtype, name, content)
        if records:
            LOGGER.debug("create_record (ignored, duplicate): %s", records[0]["id"])
            return True

        data = {"type": rtype, "name": self._relative_name(name), "value": content}

        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        result = self._post(f"/v2/domains/{self.domain}/records", data)

        if not result["uid"]:
            raise Exception("Error occured when inserting the new record.")

        LOGGER.debug("create_record: %s", result["uid"])

        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # Vercel do not allow to update a record, only add or remove.
        # So we get the corresponding record, dump or update
        # its content and insert it as a new record.
        # Then we remove the old record.
        records = []
        if identifier:
            records = self._list_records()
            records = [record for record in records if record["id"] == identifier]
        else:
            records = self._list_records(rtype, name)

        if not records:
            raise Exception(f"No record found for identifer: {identifier}")

        if len(records) > 1:
            LOGGER.warning(
                "Multiple records have been found for given parameters. "
                "Only first one will be updated (id: %s)",
                records[0]["id"],
            )

        data = {"type": rtype, "name": self._relative_name(name), "value": content}

        if not rtype:
            data["type"] = records[0]["type"]
        if not name:
            data["name"] = self._relative_name(records[0]["name"])
        if not content:
            data["value"] = records[0]["content"]
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        result = self._post(f"/v2/domains/{self.domain}/records", data)
        self._delete(f"/v2/domains/{self.domain}/records/{records[0]['id']}")

        LOGGER.debug("update_record: %s => %s", records[0]["id"], result["uid"])

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_ids)

        for delete_record_id in delete_record_ids:
            self._delete(f"/v2/domains/{self.domain}/records/{delete_record_id}")

        LOGGER.debug("delete_record: %s", True)

        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        request = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers={
                "Authorization": f"Bearer {self._get_provider_option('auth_token')}"
            },
        )

        request.raise_for_status()
        return request.json()
