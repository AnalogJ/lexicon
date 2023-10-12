"""Module provider for DNSMadeEasy"""
import hmac
import json
import logging
from argparse import ArgumentParser
from builtins import bytes
from email.utils import formatdate
from hashlib import sha1
from typing import List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class _RetryRateLimit(Retry):
    # Standard urllib3 Retry objects trigger retries only based on HTTP status code or HTTP method.
    # However we need to differentiate 400 errors with body `{"error": ["Rate limit exceeded"]}`
    # from the other 400 errors. The internal _RetryRateLimit class does that.
    def increment(
        self,
        method=None,
        url=None,
        response=None,
        error=None,
        _pool=None,
        _stacktrace=None,
    ):
        if response:
            body = json.loads(response.data)
            if "Rate limit exceeded" in body.get("error", []):
                return super(_RetryRateLimit, self).increment(
                    method, url, response, error, _pool, _stacktrace
                )

        raise RuntimeError(f"URL {url} returned a HTTP 400 status code.")


class Provider(BaseProvider):
    """Provider class for DNSMadeEasy"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["dnsmadeeasy"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-username", help="specify username for authentication"
        )
        parser.add_argument("--auth-token", help="specify token for authentication")

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = (
            self._get_provider_option("api_endpoint")
            or "https://api.dnsmadeeasy.com/V2.0"
        )

    def authenticate(self):
        try:
            payload = self._get("/dns/managed/name", {"domainname": self.domain})
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                payload = {}
            else:
                raise

        if not payload or not payload["id"]:
            raise AuthenticationError("No domain found")

        self.domain_id = payload["id"]

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing'

    def create_record(self, rtype, name, content):
        record = {
            "type": rtype,
            "name": self._relative_name(name),
            "value": content,
            "ttl": self._get_lexicon_option("ttl"),
        }
        payload = {}
        try:
            payload = self._post(f"/dns/managed/{self.domain_id}/records/", record)
        except requests.exceptions.HTTPError as error:
            if error.response.status_code != 400:
                raise

                # http 400 is ok here, because the record probably already exists
        LOGGER.debug("create_record: %s", "name" in payload)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        filter_query = {}
        if rtype:
            filter_query["type"] = rtype
        if name:
            filter_query["recordName"] = self._relative_name(name)
        payload = self._get(f"/dns/managed/{self.domain_id}/records", filter_query)

        records = []
        for record in payload["data"]:
            processed_record = {
                "type": record["type"],
                "name": f"{record['name']}.{self.domain}",
                "ttl": record["ttl"],
                "content": record["value"],
                "id": record["id"],
            }

            processed_record = self._clean_TXT_record(processed_record)
            records.append(processed_record)

        if content:
            records = [
                record
                for record in records
                if record["content"].lower() == content.lower()
            ]

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        data = {"id": identifier, "ttl": self._get_lexicon_option("ttl")}

        if name:
            data["name"] = self._relative_name(name)
        if content:
            data["value"] = content
        if rtype:
            data["type"] = rtype

        self._put(f"/dns/managed/{self.domain_id}/records/{identifier}", data)

        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self.list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_id)

        for record_id in delete_record_id:
            self._delete(f"/dns/managed/{self.domain_id}/records/{record_id}")

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-dnsme-apiKey": self._get_provider_option("auth_username"),
        }
        default_auth = None

        # Date string in HTTP format e.g. Sat, 12 Feb 2011 20:59:04 GMT
        request_date = formatdate(usegmt=True)

        hashed = hmac.new(
            bytes(self._get_provider_option("auth_token"), "ascii"),
            bytes(request_date, "ascii"),
            sha1,
        )

        default_headers["x-dnsme-requestDate"] = request_date
        default_headers["x-dnsme-hmac"] = hashed.hexdigest()

        session = requests.Session()
        try:
            # DNSMadeEasy allows only 150 requests in a floating 5 min time window.
            # So we implement a retry strategy on requests returned as 400 with body
            # `{"error": ["Rate limit exceeded"]}`.
            # 10 retries with backoff = 0.6 gives following retry delays after first attempt:
            # 1.2s, 2.4s, 4.8s, 9.6s, 19.2s, 38.4s, 76.8s, 153.6s, 307.2s
            # So last attempt is done 5 min 7 seconds after first try, so the
            # size of the floating window.
            # Beyond it we can assume something else is wrong and so give up.
            session_retries = _RetryRateLimit(
                total=10, backoff_factor=0.6, status_forcelist=[400]
            )
            session_adapter = HTTPAdapter(max_retries=session_retries)
            session.mount("http://", session_adapter)
            session.mount("https://", session_adapter)
            response = session.request(
                action,
                self.api_endpoint + url,
                params=query_params,
                data=json.dumps(data),
                headers=default_headers,
                auth=default_auth,
            )
            # if the request fails for any reason, throw an error.
            response.raise_for_status()

            # PUT and DELETE actions dont return valid json.
            if action in ["DELETE", "PUT"]:
                return response.text
            return response.json()
        finally:
            session.close()
