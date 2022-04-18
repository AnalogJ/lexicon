"""Module provider for Aurora"""
import base64
import datetime
import hashlib
import hmac
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["auroradns.eu"]


def provider_parser(subparser):
    """Configure provider parser for Aurora"""
    subparser.add_argument("--auth-api-key", help="specify API key for authentication")
    subparser.add_argument(
        "--auth-secret-key", help="specify the secret key for authentication"
    )


class Provider(BaseProvider):
    """Provider for Aurora"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.auroradns.eu"

    def _authenticate(self):
        payload = self._get("/zones")

        for item in payload:
            if item["name"] == self.domain:
                self.domain_id = item["id"]
                break
        else:
            raise AuthenticationError("No domain found")

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        data = {"type": rtype, "name": self._relative_name(name), "content": content}
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")
        payload = self._post(f"/zones/{self.domain_id}/records", data)

        LOGGER.debug("create_record: %s", payload)
        return payload

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get(f"/zones/{self.domain_id}/records")

        # Apply filtering first.
        processed_records = payload
        if rtype:
            processed_records = [
                record for record in processed_records if record["type"] == rtype
            ]
        if name:
            processed_records = [
                record
                for record in processed_records
                if record["name"] == self._relative_name(name)
            ]
        if content:
            processed_records = [
                record
                for record in processed_records
                if record["content"].lower() == content.lower()
            ]

        # Format the records.
        records = []
        for record in processed_records:
            processed_record = {
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["content"],
                "id": record["id"],
            }
            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # Try to find record if no identifier was specified
        if not identifier:
            identifier = self._find_record_identifier(rtype, name, None)

        data = {}
        if rtype:
            data["type"] = rtype
        if name:
            data["name"] = self._relative_name(name)
        if content:
            data["content"] = content
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        payload = self._put(f"/zones/{self.domain_id}/records/{identifier}", data)

        LOGGER.debug("update_record: %s", payload)
        return payload

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        # Try to find record if no identifier was specified
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)

        for record_id in delete_record_id:
            self._delete(f"/zones/{self.domain_id}/records/{record_id}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        time = datetime.datetime.utcnow()
        timestamp = time.strftime("%Y%m%dT%H%M%SZ")
        authorization_header = self._generate_auth_header(action, url, timestamp)

        request = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers={
                "X-AuroraDNS-Date": timestamp,
                "Authorization": authorization_header,
                "Content-Type": "application/json",
            },
        )

        # If the response is a HTTP 409 statusCode, the record already exists: return true.
        if request.status_code == 409:
            return True

        # If the request fails for any other reason, throw an error.
        request.raise_for_status()

        # Try to parse the json, if it not exists, return true.
        try:
            return request.json()
        except BaseException:
            return True

    def _generate_auth_header(self, action, url, timestamp):
        secret_key = self._get_provider_option("auth_secret_key")
        api_key = self._get_provider_option("auth_api_key")
        sig = action + url + timestamp

        signature = base64.b64encode(
            hmac.new(
                secret_key.encode("utf-8"),
                sig.encode("utf-8"),
                digestmod=hashlib.sha256,
            ).digest()
        )

        auth = api_key + ":" + signature.decode("utf-8")
        auth_b64 = base64.b64encode(auth.encode("utf-8"))
        return f"AuroraDNSv1 {auth_b64.decode('utf-8')}"

    def _find_record_identifier(self, rtype, name, content):
        records = self._list_records(rtype, name, content)
        LOGGER.debug("records: %s", records)
        if len(records) == 1:
            return records[0]["id"]
        raise Exception(
            "Record identifier could not be found. Try to provide an identifier"
        )
