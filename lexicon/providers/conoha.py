"""Module provider for Conoha"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["conoha.io"]


def provider_parser(subparser):
    """Configure provider parser for Conoha"""
    subparser.add_argument(
        "--auth-region", help="specify region. If empty, region `tyo1` will be used."
    )
    subparser.add_argument(
        "--auth-token",
        help=(
            "specify token for authentication. If empty, the username "
            "and password will be used to create a token."
        ),
    )
    subparser.add_argument(
        "--auth-username",
        help="specify api username for authentication. Only used if --auth-token is empty.",
    )
    subparser.add_argument(
        "--auth-password",
        help="specify api user password for authentication. Only used if --auth-token is empty.",
    )
    subparser.add_argument(
        "--auth-tenant-id",
        help="specify tenand id for authentication. Only used if --auth-token is empty.",
    )


class Provider(BaseProvider):
    """Provider class for Conoha"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None

        self.api_endpoint = "https://dns-service.{0}.conoha.io/v1".format(
            self._get_provider_option("region") or "tyo1"
        )
        self.auth_api_endpoint = "https://identity.{0}.conoha.io/v2.0".format(
            self._get_provider_option("region") or "tyo1"
        )
        self.auth_token = None

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider,
    # so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason,
    # of if the domain does not exist.
    def _authenticate(self):
        self.auth_token = self._get_provider_option("auth_token")
        if not self.auth_token:
            if not (
                self._get_provider_option("auth_username")
                and self._get_provider_option("auth_password")
            ):
                raise Exception(
                    "auth_username and auth_password or auth_token must be specified."
                )
            auth_response = self._send_request(
                "POST",
                f"{self.auth_api_endpoint}/tokens",
                {
                    "auth": {
                        "passwordCredentials": {
                            "username": self._get_provider_option("auth_username"),
                            "password": self._get_provider_option("auth_password"),
                        },
                        "tenantId": self._get_provider_option("auth_tenant_id"),
                    }
                },
            )
            self.auth_token = auth_response["access"]["token"]["id"]

        payload = self._get("/domains", {"name": self._fqdn_name(self.domain)})

        if not payload["domains"]:
            raise AuthenticationError("No domain found")
        if len(payload["domains"]) > 1:
            raise AuthenticationError("Too many domains found. This should not happen")

        self.domain_id = payload["domains"][0]["id"]

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        if not rtype:
            raise Exception("rtype must be specified.")
        if not name:
            raise Exception("name must be specified.")
        if not content:
            raise Exception("content must be specified.")
        if not self._get_lexicon_option("priority") and rtype in ("MX", "SRV"):
            raise Exception("priority must be specified.")

        try:
            self._post(
                f"/domains/{self.domain_id}/records",
                self._record_payload(rtype, name, content),
            )
        except requests.exceptions.HTTPError as err:
            # 409 Duplicate Record
            if err.response.status_code != 409:
                raise err

        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get(f"/domains/{self.domain_id}/records")
        records = payload["records"]

        if rtype:
            records = [record for record in records if record["type"] == rtype]
        if name:
            records = [
                record for record in records if record["name"] == self._fqdn_name(name)
            ]
        if content:
            records = [record for record in records if record["data"] == content]

        records = [
            {
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["data"],
                "id": record["id"],
            }
            for record in records
        ]

        LOGGER.debug("list_records: %s", records)
        return records

    # Update a record. Identifier must be specified.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier:
            records = self._list_records(rtype, name)
            if len(records) != 1:
                raise Exception("Cannot determine record")
            identifier = records[0]["id"]

        self._put(
            f"/domains/{self.domain_id}/records/{identifier}",
            self._record_payload(rtype, name, content),
        )

        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        records = self._list_records(rtype, name, content)

        if identifier:
            records = [record for record in records if record["id"] == identifier]

        for record in records:
            self._delete(f"/domains/{self.domain_id}/records/{record['id']}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        return self._send_request(
            action, f"{self.api_endpoint}{url}", data, query_params
        )

    def _send_request(self, action, url, data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = requests.request(
            action,
            url,
            data=json.dumps(data),
            params=query_params,
            headers={
                "X-Auth-Token": self.auth_token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if response.headers["content-type"].startswith("application/json"):
            return response.json()
        return response.text

    def _record_name(self, name):
        return f"{name.rstrip('.')}." if name else None

    def _record_payload(self, rtype, name, content):
        priority = self._get_lexicon_option("priority")
        ttl = self._get_lexicon_option("ttl")
        return {
            "name": self._fqdn_name(name) if name else None,
            "type": rtype,
            "data": self._record_name(content)
            if rtype in ("CNAME", "MX", "NS", "SRV")
            else content,
            "priority": int(priority) if priority else None,
            "ttl": int(ttl) if ttl else None,
        }
