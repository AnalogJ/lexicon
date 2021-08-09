"""Module provider for EasyDNS"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["easydns.net"]


def provider_parser(subparser):
    """Configure provider parser for EasyDNS"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument("--auth-token", help="specify token for authentication")


class Provider(BaseProvider):
    """Provider class for EasyDNS"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = (
            self._get_provider_option("api_endpoint") or "https://rest.easydns.net"
        )

    def _authenticate(self):

        payload = self._get(f"/domain/{self.domain}")

        if payload["data"]["exists"] == "N":
            raise AuthenticationError("No domain found")

        self.domain_id = payload["data"]["id"]

    # Create record. If record already exists with the same content, do nothing'

    def _create_record(self, rtype, name, content):
        record = {
            "type": rtype,
            "domain": self.domain_id,
            "host": self._relative_name(name),
            "ttl": self._get_lexicon_option("ttl"),
            "prio": 0,
            "rdata": content,
        }
        try:
            self._put(f"/zones/records/add/{self.domain_id}/{rtype}", record)
        except requests.exceptions.HTTPError as error:
            # FIXME: adferrand 06/01/2019: Broken provider needs fixes.
            # In fact, this except block will silently hide every HTTP error, as an except
            # block without raise statement will implicitly hide the exception.
            # In reality, tests of Easy DNS are failing...
            # So this provider needs to be corrected.
            if error.response.status_code == 400:
                pass
            # http 400 is ok here, because the record probably already exists
        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get(f"/zones/records/all/{self.domain_id}")
        records = []
        for record in payload["data"]:
            processed_record = {
                "type": record["type"],
                "name": f"{record['host']}.{record['domain']}",
                "ttl": record["ttl"],
                "content": record["rdata"],
                "id": record["id"],
            }
            records.append(processed_record)

        if rtype:
            records = [record for record in records if record["type"] == rtype]
        if name:
            records = [
                record for record in records if record["name"] == self._full_name(name)
            ]
        if content:
            records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        data = {"ttl": self._get_lexicon_option("ttl")}
        if rtype:
            data["type"] = rtype
        if name:
            data["host"] = self._relative_name(name)
        if content:
            data["rdata"] = content

        self._post(f"/zones/records/{identifier}", data)

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
            self._delete(f"/zones/records/{self.domain_id}/{record_id}")

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        query_params["format"] = "json"
        query_params["_user"] = self._get_provider_option("auth_username")
        query_params["_key"] = self._get_provider_option("auth_token")
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()
