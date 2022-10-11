"""Module provider for Yandex.Cloud DNS

API doc: https://cloud.yandex.com/en/docs/dns/

If you are using the service account, dns.viewer required for viewing the DNS records
and dns.editor for editing them.

If Cloud ID and Folder ID are not specified,
resource-manager.clouds.member and resource-manager.viewer are needed as well.
"""
import hashlib
import json
import logging
import urllib
from typing import Dict, List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

__author__ = "Dmitry Verkhoturov"
__license__ = "MIT"
__contact__ = "https://github.com/paskal"

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["yandexcloud.net"]


def provider_parser(subparser):
    """Generate parser provider for Yandex"""
    subparser.add_argument(
        "--auth-token",
        help="specify the IAM token (https://cloud.yandex.com/en/docs/dns/api-ref/authentication)",
    )
    subparser.add_argument(
        "--dns-zone-id",
        help="specify the DNS Zone ID (can be obtained from web interface)",
    )
    subparser.add_argument(
        "--cloud-id",
        help="specify the Cloud ID (visible in the cloud selector in the web interface), might be needed"
        " if DNS zone ID is not set",
    )
    subparser.add_argument(
        "--folder-id",
        help="specify the Folder ID (https://cloud.yandex.com/en/docs/resource-manager/operations/folder/get-id) "
        "might be needed if DNS zone ID is not set",
    )


class Provider(BaseProvider):
    """Provider class for Yandex Cloud"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.default_ttl = 600  # 10 minutes: default value, used in Yandex.Cloud DNS
        self.api_endpoint = "https://dns.api.cloud.yandex.net/dns/v1"
        self.resources_api_endpoint = (
            "https://resource-manager.api.cloud.yandex.net/resource-manager/v1"
        )

    def _full_name_with_dot(self, s: str) -> str:
        return self._full_name(s) + "."

    @staticmethod
    def _identifier(rtype: str, name: str, content: str) -> str:
        sha256 = hashlib.sha256()
        sha256.update(("type=" + rtype + ",").encode("utf-8"))
        sha256.update(("name=" + name + ",").encode("utf-8"))
        sha256.update(("data=" + content).encode("utf-8"))
        return sha256.hexdigest()[0:7]

    def _authenticate(self):
        dns_zone_id = self._get_provider_option("dns_zone_id")
        if dns_zone_id and self._cloud_id_matches_domain(dns_zone_id):
            self.domain_id = dns_zone_id

        # in case DNS zone ID is not set or set but not valid, fall back to retrieving it from the list
        if not self.domain_id:
            cloud_id = self._get_cloud_id()
            folder_id = self._get_folder_id(cloud_id)
            self.domain_id = self._get_dns_zone_id(folder_id)

    # verifies that the domain ID matches the domain in question
    def _cloud_id_matches_domain(self, dns_zone_id: str) -> bool:
        payload: Dict = self._get(f"{self.api_endpoint}/zones/{dns_zone_id}")
        if "zone" not in payload:
            # No DNS zone with given ID found
            return True
        if payload["zone"] != f"{self.domain}.":
            # Provided DNS zone ID does not match the domain
            return False
        return True

    def _get_cloud_id(self) -> str:
        """Gets Cloud ID from Resource Manager API
        https://cloud.yandex.com/en/docs/resource-manager/api-ref/Cloud/list"""
        if self._get_provider_option("cloud_id"):
            return self._get_provider_option("cloud_id")

        payload: Dict = self._get(f"{self.resources_api_endpoint}/clouds")

        if "clouds" not in payload:
            raise AuthenticationError("No clouds found")
        if len(payload["clouds"]) > 1:
            raise AuthenticationError(
                "Too many clouds found, you must specify one explicitly, or set DNS zone ID"
            )

        return payload["clouds"][0]["id"]

    def _get_folder_id(self, cloud_id: str) -> str:
        """Gets Folder ID from Resource Manager API
        https://cloud.yandex.com/en/docs/resource-manager/api-ref/Folder/list
        """
        if self._get_provider_option("folder_id"):
            return self._get_provider_option("folder_id")

        payload: Dict = self._get(
            f"{self.resources_api_endpoint}/folders", {"cloudId": cloud_id}
        )

        if "folders" not in payload:
            raise AuthenticationError(f"No folders found for Cloud ID {cloud_id}")
        if len(payload["folders"]) > 1:
            raise AuthenticationError(
                "Too many folders found, you must specify one explicitly, or set DNS zone ID"
            )

        return payload["folders"][0]["id"]

    def _get_dns_zone_id(self, folder_id: str) -> str:
        """Gets Domain ID from DnsZone API
        https://cloud.yandex.com/en/docs/dns/api-ref/DnsZone/list
        """
        payload: Dict = self._get(
            "/zones", {"folderId": folder_id, "filter": f"zone='{self.domain}.'"}
        )

        if "dnsZones" not in payload:
            raise AuthenticationError(f"No domain found for Folder ID {folder_id}")
        if len(payload["dnsZones"]) > 1:
            raise AuthenticationError("Too many domains found, this should not happen")

        return payload["dnsZones"][0]["id"]

    def _list_records(self, rtype=None, name=None, content=None) -> List[Dict]:
        """List all records. Return an empty list if no records found.
        type, name and content are used to filter records.
        https://cloud.yandex.com/en/docs/dns/api-ref/DnsZone/listRecordSets
        """
        records: List[Dict] = []

        query_params = {"filter": ""}
        if rtype:
            query_params["filter"] = f"type='{rtype}'"

        # name should be in full form, transform it in case it's not
        if name:
            name = self._full_name_with_dot(name)
            query_params["filter"] += " AND " if query_params["filter"] else ""
            query_params["filter"] += f"name='{name}'"

        url = f"/zones/{self.domain_id}:listRecordSets"
        more_pages = True
        while more_pages:
            payload: Dict = self._get(url, query_params)
            if "nextPageToken" in payload:
                query_params["pageToken"] = payload["nextPageToken"]
            else:
                more_pages = False

            # nothing to list
            if "recordSets" not in payload:
                break

            for record in payload["recordSets"]:
                for entry in record["data"]:
                    # artificially generate ID for deletion and update
                    records.append(
                        {
                            "id": self._identifier(
                                record["type"], record["name"], entry
                            ),
                            "name": self._full_name(record["name"]),
                            "type": record["type"],
                            "ttl": record["ttl"],
                            "content": entry,
                        }
                    )

        if content:
            records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: %s", records)
        return records

    def _get_record(self, identifier="", rtype="", name="") -> Dict:
        """Gets a single record by rtype and name, or by identifier.
        Throws HTTPError with status code 404 if record not found.
        https://cloud.yandex.com/en/docs/dns/api-ref/DnsZone/getRecordSet"""

        # find entry by identifier if it was provided.
        # the output format for _list_records and _get_record is different,
        # so it's necessary to find an entry in _list_records and then
        # re-request it in this function
        if identifier:
            for record in self._list_records():
                if record["id"] == identifier:
                    rtype = record["type"]
                    name = record["name"]

        if name is not None:
            name = self._full_name_with_dot(name)

        url = f"/zones/{self.domain_id}:getRecordSet"
        query_params = {"name": name, "type": rtype}
        # name should be in full form, transform it in case it's not

        return self._get(url, query_params)

    def _create_record(self, rtype, name, content):
        """Create a record. Return True if record was created, or already the same precise record exists,
        False if record already exists or there is another problem.
        All params are required.
        """

        # name should be in full form, transform it in case it's not
        if name is not None:
            name = self._full_name_with_dot(name)

        # get existing content
        data = [content]
        try:
            record = self._get_record(rtype=rtype, name=name)
            data = record["data"]
            # add new content entry only if it's not yet present
            if content not in record["data"]:
                data.append(content)
        except requests.exceptions.HTTPError as error:
            if error.response.status_code != 404:
                raise error

        payload = self._post(
            f"/zones/{self.domain_id}:upsertRecordSets",
            {
                "replacements": [
                    {
                        "name": name,
                        "type": rtype,
                        "ttl": self._get_lexicon_option("ttl") or self.default_ttl,
                        "data": data,
                    }
                ]
            },
        )

        return self._check_request_success(payload, "create_record")

    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        """Update existing record."""

        record = {
            "name": name,
            "type": rtype,
            "ttl": self._get_lexicon_option("ttl") or self.default_ttl,
            "data": content.split("\n"),
        }

        try:
            if identifier:
                record = self._get_record(identifier)
                if content and content in record["data"] and len(record["data"]) > 1:
                    # identifier is associated with particular content line
                    for i, entry in enumerate(record["data"]):
                        if identifier == self._identifier(
                            record["type"], record["name"], entry
                        ):
                            del record["data"][i]
                            record["data"].extend(content.split("\n"))
                            break
                # if we have the name and type alongside with id, use them instead of retrieved ones
                if name:
                    record["name"] = name
                if rtype:
                    record["type"] = rtype
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                LOGGER.info("update_record: identifier=%s does not exist", identifier)
                return True
            raise error

        payload = self._post(
            f"/zones/{self.domain_id}:upsertRecordSets", {"replacements": [record]}
        )
        return self._check_request_success(payload, "update_record")

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """Delete an existing record. Do nothing if record does not exist."""
        # name should be in full form, transform it in case it's not
        if name is not None:
            name = self._full_name_with_dot(name)

        try:
            record = self._get_record(identifier, rtype, name)
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                LOGGER.info(
                    "delete_record: id=%s type=%s name=%s does not exist",
                    identifier,
                    rtype,
                    name,
                )
                return True
            raise error

        # remove content entry if it's one of the many, and update record instead of deleting it
        action = "deletions"
        if content and content in record["data"] and len(record["data"]) > 1:
            record["data"].remove(content)
            action = "replacements"

        # deletion requires full match on also TTL and data, which would require us to find such entry first
        payload = self._post(
            f"/zones/{self.domain_id}:upsertRecordSets", {action: [record]}
        )

        return self._check_request_success(payload, "delete_record")

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None) -> Dict:
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        auth_token = self._get_provider_option("auth_token")

        if not auth_token:
            raise Exception("auth_token must be specified.")

        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {auth_token}",
        }

        if not url.startswith("https://"):
            url = self.api_endpoint + url

        # urllib required here as requests by default encodes spaces as plus symbol (+) instead of %20
        response = requests.request(
            action,
            url,
            params=urllib.parse.urlencode(query_params, quote_via=urllib.parse.quote),
            data=json.dumps(data),
            headers=default_headers,
        )
        # if the request fails for any reason, throw an error.
        # response.raise_for_status() will throw and error, so the line below is just logging
        if "code" in response.json():
            LOGGER.warning(
                "error making request: %d, %s",
                response.json()["code"],
                response.json()["message"],
            )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _check_request_success(payload, title):
        if "code" in payload:
            LOGGER.debug("%s: code %d, %s", title, payload["code"], payload["message"])
            return False

        LOGGER.debug("%s: %s", title, payload)
        return True
