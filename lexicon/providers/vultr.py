"""Module provider for Vultr"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["vultr.com"]


def provider_parser(subparser):
    """Configure provider parser for Vultr"""
    subparser.add_argument("--auth-token", help="specify token for authentication")


class Provider(BaseProvider):
    """Provider class for Vultr"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.vultr.com/v2"

    def _authenticate(self):
        payload = self._get("/domains")

        for domain in payload["domains"]:
            if domain["domain"] == self.domain:
                self.domain_id = self.domain
                return

        while payload["meta"]["links"]["next"] != "":
            query_params = {"cursor": payload["meta"]["links"]["next"]}
            payload = self._get("/domains", query_params=query_params)

            for domain in payload["domains"]:
                if domain["domain"] == self.domain:
                    self.domain_id = self.domain
                    return

        raise AuthenticationError("Domain not found")

    # Create record. If record already exists with the same content, do nothing
    def _create_record(self, rtype, name, content):
        records = self._list_records(rtype, name, content)
        if len(records) != 0:
            LOGGER.debug("create_record (already exists): %s", records[0]["id"])
            return True

        record = {
            "type": rtype,
            "name": self._relative_name(name),
            "data": self._add_quotes(rtype, content),
            "priority": 0,
        }
        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        result = self._post(f"/domains/{self.domain_id}/records", record)
        LOGGER.debug("create_record: %s", result["record"]["id"])
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        url = f"/domains/{self.domain_id}/records"

        payload = self._get(url)
        unprocessed_records = payload["records"]

        while payload["meta"]["links"]["next"] != "":
            query_params = {"cursor": payload["meta"]["links"]["next"]}
            payload = self._get(url, query_params=query_params)
            unprocessed_records.extend(payload["records"])

        records = []
        for record in unprocessed_records:
            records.append(self._process_record(record))

        if rtype:
            records = [rec for rec in records if rec["type"] == rtype]
        if name:
            records = [rec for rec in records if rec["name"] == self._full_name(name)]
        if content:
            records = [rec for rec in records if rec["content"] == content]

        LOGGER.debug("list_records: %s", records)
        return records

    # Update a record. Identifier must be specified.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        record = None
        if not identifier:
            records = self._list_records(rtype, name)

            if not records:
                raise Exception(
                    f"No record(s) found for arguments: identifer={identifier}, rtype={rtype}, name={name}"
                )
            if len(records) > 1:
                LOGGER.warning(
                    "Multiple records have been found for given parameters. "
                    "Only first one will be updated (id: %s)",
                    records[0]["id"],
                )

            record = records[0]
            identifier = record["id"]

        url = f"/domains/{self.domain_id}/records/{identifier}"
        if not record:
            record = self._get(url)["record"]
            record = self._process_record(record)

        new_record = {}

        if name:
            name = self._relative_name(name)
            if name != record["name"]:
                new_record["name"] = name

        if content:
            content = self._add_quotes(record["type"], content)
            if content != record["content"]:
                new_record["data"] = content

        if new_record == {}:
            LOGGER.debug("update_record (nothing to do): %s", True)
            return True

        self._patch(url, new_record)
        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)
        for record_id in delete_record_id:
            try:
                self._delete(f"/domains/{self.domain_id}/records/{record_id}")
            except requests.HTTPError as e:
                if e.response.status_code != 404:
                    raise

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self._get_provider_option("auth_token"),
        }

        if data is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data)

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=data,
            headers=headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()

        if response.status_code == 204:
            return None

        return response.json()

    @staticmethod
    def _add_quotes(rtype, content):
        if rtype == "TXT":
            return f'"{content}"'
        return content

    def _process_record(self, record):
        processed_record = {
            "type": record["type"],
            "name": self._full_name(record["name"]),
            "ttl": record["ttl"],
            "content": record["data"],
            "id": record["id"],
        }
        return self._clean_TXT_record(processed_record)
