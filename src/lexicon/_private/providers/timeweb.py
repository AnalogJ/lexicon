"""Module provider for Timeweb"""

import json
import logging
from argparse import ArgumentParser
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

# Timeweb API does not support TTL. All records get 600 by default.
DEFAULT_TTL = 600
DEFAULT_PAGE_SIZE = 100


class Provider(BaseProvider):
    """
    Implements Timeweb DNS provider: https://timeweb.cloud.
    See also API documentation: https://timeweb.cloud/api-docs#tag/Domeny
    """

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["timeweb.cloud"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-token",
            help="specify API token for authentication",
        )

    @staticmethod
    def _check_ok(result) -> bool:
        error_code = result.get("error_code")
        if error_code:
            status_code = result["status_code"]
            message = result["message"]
            LOGGER.error(f"Status code: {status_code}. {message}")
            return False
        else:
            return True

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.timeweb.cloud/api/v1"
        self.api_dns = f"/domains/{self.domain}"
        self.api_dns_records = f"{self.api_dns}/dns-records"

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        else:
            LOGGER.debug(f"Preparing data: {data}")
        if query_params is None:
            query_params = {}
        else:
            LOGGER.debug(f"Preparing query params: {query_params}")
        full_url = self.api_endpoint + url
        LOGGER.debug(f"Sending {action} {full_url}")
        response = requests.request(
            action,
            full_url,
            params=query_params,
            data=json.dumps(data),
            headers={
                "Authorization": f'Bearer {self._get_provider_option("auth_token")}',
                "Content-Type": "application/json",
            },
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        r_json = response.json() if response.content else {}
        LOGGER.debug(f"Result: {r_json}")
        return r_json

    def _get_subdomain(self, record_name):
        if record_name.rstrip(".").endswith(self.domain):
            record_name = self._relative_name(record_name)
        return record_name

    def authenticate(self):
        result = self._get(self.api_dns)
        if self._check_ok(result):
            self.domain_id = result["domain"]["id"]
        else:
            raise AuthenticationError(f"Domain {self.domain} not found.")

    def create_record(self, rtype, name, content):
        data = {
            "subdomain": self._get_subdomain(name),
            "type": rtype,
            "value": content,
        }
        try:
            result = self._post(self.api_dns_records, data)
            return self._check_ok(result)
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 409:
                LOGGER.warning(
                    f"Record {rtype} {name} returns {status_code} (already exists?)"
                )
                return True
            raise e

    def list_records(self, rtype=None, name=None, content=None):
        records = []
        processed_records = 0
        while True:
            query_params = {"limit": DEFAULT_PAGE_SIZE, "offset": processed_records}
            result = self._get(self.api_dns_records, query_params=query_params)
            if not self._check_ok(result):
                break
            for record in result["dns_records"]:
                r_rtype = record["type"]
                r_name = record["data"].get("subdomain", self.domain)
                r_content = record["data"]["value"]
                processed_record = {
                    "type": r_rtype,
                    "name": self._full_name(name) if name else r_name,
                    "ttl": DEFAULT_TTL,
                    "content": r_content,
                    "id": record["id"],
                }
                if (
                    (rtype is None or r_rtype == rtype)
                    and (name is None or r_name == self._get_subdomain(name))
                    and (content is None or r_content == content)
                ):
                    records.append(processed_record)
                processed_records += 1

            total_records = result["meta"]["total"]
            if processed_records >= total_records:
                break

        LOGGER.debug(f"list_records: {records}")
        LOGGER.debug(f"Number of records retrieved: {len(records)}")
        return records

    def update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier is None:
            records = self.list_records(rtype, name)
            if len(records) == 1:
                record = records[0]
                identifier = str(record["id"])
            elif len(records) < 1:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )
        else:
            records = self.list_records()
            record = next((r for r in records if str(r["id"]) == identifier), None)

        data = {
            "subdomain": self._get_subdomain(name) if name else record["name"],
            "type": rtype if rtype else record["type"],
            "value": content if content else record["content"],
        }
        result = self._patch(f"{self.api_dns_records}/{identifier}", data)

        LOGGER.debug(f"update_record: {result}")
        return self._check_ok(result)

    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if name:
            name = self._get_subdomain(name)
        if not identifier:
            records = self.list_records(rtype, name, content)
            ids_to_delete = [r["id"] for r in records]
        else:
            ids_to_delete = [identifier]

        if ids_to_delete:
            overall_ok = True
            for id_to_delete in ids_to_delete:
                result = self._delete(f"{self.api_dns_records}/{id_to_delete}")
                if self._check_ok(result):
                    LOGGER.debug(f"Successfully deleted record {id_to_delete}")
                else:
                    overall_ok = False
            return overall_ok
        else:
            LOGGER.warning("delete_record: no record found")
            return False
