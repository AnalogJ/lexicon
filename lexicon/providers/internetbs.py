"""
The internetbs api has an undocumented rate-limit ; here is what the support could tell me about
it: "Please note that our API is intended mainly for domain name registrations and that's why we
offer it for free and your registration volume has to stay in phase with the requests you perform.
If you keep a reasonable ratio between check and successful registrations, you should never hit
the limits. Here are the limits:
- per minute = 60+N
- per hour = 500+N
- per day = 1000+2*N
- per week = 2000+2.5*N
- per month = 3000+3*N
Where N is the number of registered domains in your account (so excluding pending
transfers/trades)."
"""
import hashlib
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["topdns.com"]


def provider_parser(subparser):
    """Configure provider parser for internetbs"""
    subparser.add_argument("--auth-key", help="specify API key for authentication")
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )


class Provider(BaseProvider):
    """Provider class for internetbs"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.internet.bs"

    def _authenticate(self):
        payload = self._get("/Domain/List", {"searchTermFilter": self.domain})

        LOGGER.debug("authenticate debug: %s", payload)
        if not payload["status"]:
            raise AuthenticationError("Internal error. This should not happen")
        if payload["status"] != "SUCCESS":
            raise AuthenticationError(f"Api error: {payload['message']}")
        if self.domain not in payload["domain"]:
            raise AuthenticationError("Domain not found")
        self.domain_id = self.domain

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        # Skip execution if such a record already exists
        existing_records = self._list_records(rtype, name, content)
        if existing_records:
            return True

        query = {
            "Type": rtype,
            "FullRecordName": self._full_name(name),
            "Value": content,
        }
        ttl = self._get_lexicon_option("ttl")
        if ttl:
            query["Ttl"] = ttl

        # for MX records, query['Priority'] could be set (default is 10)

        payload = self._post("/Domain/DnsRecord/Add", None, query)
        LOGGER.debug("authenticate debug: %s", payload)
        if not payload["status"]:
            raise Exception("Internal error. This should not happen")
        if payload["status"] != "SUCCESS":
            raise Exception(f"Api error: {payload['message']}")
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        query = {"Domain": self.domain}
        if rtype:
            query["FilterType"] = rtype

        payload = self._get("/Domain/DnsRecord/List", query)
        if payload["status"] != "SUCCESS":
            raise Exception(f"Api status: {payload['status']}")
        if payload["total_records"] == 0:
            return []

        record_list = payload["records"]
        if name:
            cmp_name = self._relative_name(name.lower())
            record_list = [
                record
                for record in record_list
                if self._relative_name(record["name"]) == cmp_name
            ]
        if content:
            record_list = [
                record for record in record_list if record["value"] == content
            ]

        records = []
        for record in record_list:
            processed_record = {
                "type": record["type"],
                "name": record["name"],
                "ttl": record["ttl"],
                "content": record["value"],
                # internetbs api does not provide id
                "id": hashlib.sha1(
                    "/".join([record["type"], record["name"], record["value"]]).encode(
                        "utf-8"
                    )
                ).hexdigest(),
            }
            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    # Update a record.
    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            records = self._list_records()
            to_update = next((r for r in records if r["id"] == identifier), None)
            query = {
                "Type": to_update["type"],
                "FullRecordName": to_update["name"],
                "NewValue": content,
            }
        else:
            query = {
                "Type": rtype,
                "FullRecordName": self._full_name(name),
                "NewValue": content,
            }
        LOGGER.debug("update_record query: %s", query)
        payload = self._post("/Domain/DnsRecord/Update", None, query)
        LOGGER.debug("update_record payload: %s", payload)

        if not payload["status"]:
            raise Exception("Internal error. This should not happen")
        if payload["status"] != "SUCCESS":
            raise Exception(f"Api error: {payload['message']}")
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            records = self._list_records()
            to_update = next((r for r in records if r["id"] == identifier), None)
            if not to_update:
                return True
            query = {
                "Type": to_update["type"],
                "FullRecordName": to_update["name"],
                "NewValue": content,
            }
        else:
            query = {"Type": rtype, "FullRecordName": self._full_name(name)}
            if content:
                query["Value"] = content
                if not self._list_records(rtype, name, content):
                    return True
            else:
                if not self._list_records(rtype, name):
                    return True

        LOGGER.debug("delete_record query: %s", query)
        payload = self._post("/Domain/DnsRecord/Remove", None, query)
        LOGGER.debug("delete_record payload: %s", payload)

        if not payload["status"]:
            raise Exception("Internal error. This should not happen")
        if payload["status"] != "SUCCESS":
            raise Exception(f"Api error: {payload['message']}")
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        query_params["ResponseFormat"] = "json"
        query_params["ApiKey"] = self._get_provider_option("auth_key")
        query_params["Password"] = self._get_provider_option("auth_password")
        request = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )
        # if the request fails for any reason, throw an error.
        request.raise_for_status()
        return request.json()
