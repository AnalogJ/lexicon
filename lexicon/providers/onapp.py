"""Module provider for OnApp"""
import json
import logging
from typing import List

import requests
from requests.auth import HTTPBasicAuth

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS: List[str] = []


def provider_parser(subparser):
    """Configure provider parser for OnApp"""
    subparser.description = """
        The OnApp provider requires your OnApp account\'s email address and
        API token, which can be found on your /profile page on the Control Panel interface.
        The server is your dashboard URL, with format like https://dashboard.youronapphost.org"""
    subparser.add_argument(
        "--auth-username", help="specify email address of the OnApp account"
    )
    subparser.add_argument("--auth-token", help="specify API Key for the OnApp account")
    subparser.add_argument(
        "--auth-server", help="specify URL to the OnApp Control Panel Server"
    )


class Provider(BaseProvider):
    """Provider class for OnApp"""

    def __init__(self, config):
        super(Provider, self).__init__(config)

        self.domain_id = None

        if not self._get_provider_option("auth_username"):
            raise Exception("Error, OnApp Email Address is not defined")
        if not self._get_provider_option("auth_token"):
            raise Exception("Error, OnApp API Key is not defined")
        if not self._get_provider_option("auth_server"):
            raise Exception("Error, OnApp Control Panel URL is not defined")

        self.session = requests.Session()

    def _authenticate(self):
        domain = self.domain

        zones = self._get("/dns_zones.json")
        for zone in zones:
            if zone["dns_zone"]["name"] == domain:
                self.domain_id = zone["dns_zone"]["id"]
                break
        else:
            raise AuthenticationError(f"Could not find {domain} in OnApp DNS Zones")

    def _create_record(self, rtype, name, content):
        data = {
            "name": self._relative_name(name),
            "type": rtype,
            self._key_for_record_type(rtype): content,
        }

        ttl = self._get_lexicon_option("ttl")
        if ttl:
            data["ttl"] = f"{ttl}"

        result = self._post(
            f"/dns_zones/{self.domain_id}/records.json", {"dns_record": data}
        )
        LOGGER.debug("create_record: %s", result)

        return True

    def _list_records(self, rtype=None, name=None, content=None):
        records = []

        response = self._get(f"/dns_zones/{self.domain_id}/records.json")
        for record_type in response["dns_zone"]["records"]:

            # For now we do not support other RR types so we ignore them, also see
            # _key_for_record_type
            if record_type not in ("A", "AAAA", "CNAME", "TXT"):
                continue

            if rtype and record_type != rtype:
                continue

            for record in response["dns_zone"]["records"][record_type]:
                record = record["dns_record"]

                if name and record["name"] != self._relative_name(name):
                    continue

                record_content = record[self._key_for_record_type(record_type)]
                if content and record_content != content:
                    continue

                records.append(
                    {
                        "id": record["id"],
                        "name": self._full_name(record["name"]),
                        "type": record["type"],
                        "ttl": record["ttl"],
                        "content": record_content,
                    }
                )

        LOGGER.debug("list_records: %s", records)

        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier:
            existing = self._guess_record(rtype, name)
            identifier = existing["id"]

        ttl = self._get_lexicon_option("ttl")

        if not name or not ttl:
            if not existing:
                existing = self._get(
                    f"/dns_zones/{self.domain_id}/records/{identifier}.json"
                )
            if not name:
                name = existing["name"]
            if not ttl:
                ttl = existing["ttl"]

        request = {
            "name": self._relative_name(name),
            "ttl": f"{ttl}",
            self._key_for_record_type(rtype): content,
        }

        result = self._put(
            f"/dns_zones/{self.domain_id}/records/{identifier}.json",
            {"dns_record": request},
        )
        LOGGER.debug("update_record: %s", result)

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        deletion_ids = []

        if not identifier:
            records = self._list_records(rtype, name, content)
            deletion_ids = [record["id"] for record in records]
        else:
            deletion_ids.append(identifier)

        for one_id in deletion_ids:
            self._delete(f"/dns_zones/{self.domain_id}/records/{one_id}.json")

        LOGGER.debug("delete_record: %s", True)

        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        target = self._get_provider_option("auth_server") + url

        body = ""
        if data is not None:
            body = json.dumps(data)

        auth = HTTPBasicAuth(
            self._get_provider_option("auth_username"),
            self._get_provider_option("auth_token"),
        )

        request = requests.Request(
            action, target, data=body, headers=headers, params=query_params, auth=auth
        )
        prepared_request = self.session.prepare_request(request)

        result = self.session.send(prepared_request)
        result.raise_for_status()

        if result.text:
            return result.json()
        return None

    def _key_for_record_type(self, record_type):
        if record_type in ("A", "AAAA"):
            return "ip"
        if record_type == "CNAME":
            return "hostname"
        if record_type == "TXT":
            return "txt"
        if record_type in ("MX", "NS", "SOA", "SRV", "LOC"):
            raise Exception(
                f"{record_type} record type is not supported in the OnApp Provider"
            )
        raise Exception(f"{record_type} record type is unknown")

    def _guess_record(self, rtype, name=None, content=None):
        records = self._list_records(rtype=rtype, name=name, content=content)
        if len(records) == 1:
            return records[0]
        if len(records) > 1:
            raise Exception(
                "Identifier was not provided and several existing records "
                "match the request for {0}/{1}".format(rtype, name)
            )
        raise Exception(
            "Identifier was not provided and no existing records "
            "match the request for {0}/{1}".format(rtype, name)
        )
