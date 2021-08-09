"""Module provider for OVH"""
import hashlib
import json
import logging
import time

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

ENDPOINTS = {
    "ovh-eu": "https://eu.api.ovh.com/1.0",
    "ovh-ca": "https://ca.api.ovh.com/1.0",
    "ovh-us": "https://api.ovhcloud.com/1.0",
    "kimsufi-eu": "https://eu.api.kimsufi.com/1.0",
    "kimsufi-ca": "https://ca.api.kimsufi.com/1.0",
    "soyoustart-eu": "https://eu.api.soyoustart.com/1.0",
    "soyoustart-ca": "https://ca.api.soyoustart.com/1.0",
}

NAMESERVER_DOMAINS = ["ovh.net", "anycast.me"]


def provider_parser(subparser):
    """Generate provider parser for OVH"""
    subparser.description = """
        OVH Provider requires a token with full rights on /domain/*.
        It can be generated for your OVH account on the following URL:
        https://api.ovh.com/createToken/index.cgi?GET=/domain/*&PUT=/domain/*&POST=/domain/*&DELETE=/domain/*"""
    subparser.add_argument(
        "--auth-entrypoint",
        help="specify the OVH entrypoint",
        choices=[
            "ovh-eu",
            "ovh-ca",
            "soyoustart-eu",
            "soyoustart-ca",
            "kimsufi-eu",
            "kimsufi-ca",
        ],
    )
    subparser.add_argument("--auth-application-key", help="specify the application key")
    subparser.add_argument(
        "--auth-application-secret", help="specify the application secret"
    )
    subparser.add_argument("--auth-consumer-key", help="specify the consumer key")


class Provider(BaseProvider):
    """Provider class for OVH"""

    def __init__(self, config):
        super(Provider, self).__init__(config)

        # Handling missing required parameters
        if not self._get_provider_option("auth_entrypoint"):
            raise Exception("Error, entrypoint is not defined")
        if not self._get_provider_option("auth_application_key"):
            raise Exception("Error, application key is not defined")
        if not self._get_provider_option("auth_application_secret"):
            raise Exception("Error, application secret is not defined")
        if not self._get_provider_option("auth_consumer_key"):
            raise Exception("Error, consumer key is not defined")

        # Construct DNS OVH environment
        self.domain_id = None
        self.endpoint_api = ENDPOINTS.get(self._get_provider_option("auth_entrypoint"))
        self.session = None
        self.time_delta = None

    def _authenticate(self):
        # All requests will be done in one HTTPS session
        self.session = requests.Session()

        # Calculate delta time between local and OVH to avoid requests rejection
        server_time = self.session.get(f"{self.endpoint_api}/auth/time").json()
        self.time_delta = server_time - int(time.time())

        # Get domain and status
        domain = self.domain

        domains = self._get("/domain/zone/")
        if domain not in domains:
            raise AuthenticationError(f"Domain {domain} not found")

        status = self._get(f"/domain/zone/{domain}/status")
        if not status["isDeployed"]:
            raise AuthenticationError(f"Zone {domain} is not deployed")

        self.domain_id = domain

    def _create_record(self, rtype, name, content):
        domain = self.domain
        ttl = self._get_lexicon_option("ttl")

        records = self._list_records(rtype, name, content)
        for record in records:
            if (
                record["type"] == rtype
                and self._relative_name(record["name"]) == self._relative_name(name)
                and record["content"] == content
            ):
                LOGGER.debug(
                    "create_record (ignored, duplicate): %s %s %s", rtype, name, content
                )
                return True

        data = {
            "fieldType": rtype,
            "subDomain": self._relative_name(name),
            "target": content,
        }

        if ttl:
            data["ttl"] = ttl

        result = self._post(f"/domain/zone/{domain}/record", data)
        self._post(f"/domain/zone/{domain}/refresh")

        LOGGER.debug("create_record: %s", result["id"])

        return True

    def _list_records(self, rtype=None, name=None, content=None):
        domain = self.domain
        records = []

        params = {}
        if rtype:
            params["fieldType"] = rtype
        if name:
            params["subDomain"] = self._relative_name(name)

        record_ids = self._get(f"/domain/zone/{domain}/record", params)

        for record_id in record_ids:
            raw = self._get(f"/domain/zone/{domain}/record/{record_id}")
            records.append(
                {
                    "type": raw["fieldType"],
                    "name": self._full_name(raw["subDomain"]),
                    "ttl": raw["ttl"],
                    "content": raw["target"],
                    "id": raw["id"],
                }
            )

        if content:
            records = [
                record
                for record in records
                if record["content"].lower() == content.lower()
            ]

        LOGGER.debug("list_records: %s", records)

        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        domain = self.domain

        if not identifier:
            records = self._list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            elif len(records) > 1:
                raise Exception("Several record identifiers match the request")
            else:
                raise Exception("Record identifier could not be found")

        data = {}
        if name:
            data["subDomain"] = self._relative_name(name)
        if content:
            data["target"] = content

        self._put(f"/domain/zone/{domain}/record/{identifier}", data)
        self._post(f"/domain/zone/{domain}/refresh")

        LOGGER.debug("update_record: %s", identifier)

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        domain = self.domain

        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)

        for record_id in delete_record_id:
            self._delete(f"/domain/zone/{domain}/record/{record_id}")

        self._post(f"/domain/zone/{domain}/refresh")

        LOGGER.debug("delete_record: %s", True)

        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        headers = {}
        target = self.endpoint_api + url
        body = ""

        if data is not None:
            headers["Content-type"] = "application/json"
            body = json.dumps(data)

        # Get correctly sync time
        now = str(int(time.time()) + self.time_delta)

        headers["X-Ovh-Application"] = self._get_provider_option("auth_application_key")
        headers["X-Ovh-Consumer"] = self._get_provider_option("auth_consumer_key")
        headers["X-Ovh-Timestamp"] = now

        request = requests.Request(
            action, target, data=body, params=query_params, headers=headers
        )
        prepared_request = self.session.prepare_request(request)

        # Build OVH API signature for the current request
        signature = hashlib.sha1()
        signature.update(
            "+".join(
                [
                    self._get_provider_option("auth_application_secret"),
                    self._get_provider_option("auth_consumer_key"),
                    action.upper(),
                    prepared_request.url,
                    body,
                    now,
                ]
            ).encode("utf-8")
        )

        # Sign the request
        headers["X-Ovh-Signature"] = "$1$" + signature.hexdigest()

        result = self.session.request(
            method=action, url=target, params=query_params, data=body, headers=headers
        )
        result.raise_for_status()

        return result.json()
