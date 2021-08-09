"""Module provider for Njalla"""
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["1-you.njalla.no", "2-can.njalla.in", "3-get.njalla.fo"]


def provider_parser(subparser):
    """Module provider for Njalla"""
    subparser.add_argument("--auth-token", help="specify API token for authentication")


class Provider(BaseProvider):
    """Provider class for Njalla"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://njal.la/api/1/"

    def _authenticate(self):
        params = {"domain": self.domain}
        try:
            result = self._api_call("get-domain", params)
        except Exception as e:
            raise AuthenticationError(str(e))

        if result["name"] != self.domain:
            raise AuthenticationError("Domain not found")

        self.domain_id = self.domain

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        params = {
            "domain": self.domain,
            "type": rtype,
            "name": name,
            "content": content,
            "ttl": 10800,
        }
        if self._get_lexicon_option("ttl"):
            params["ttl"] = self._get_lexicon_option("ttl")
        result = self._api_call("add-record", params)

        LOGGER.debug("create_record: %s", result)
        return result

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        params = {"domain": self.domain}
        result = self._api_call("list-records", params)

        records = result["records"]
        processed_records = [
            {
                "id": record["id"],
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["content"],
            }
            for record in records
        ]
        filtered_records = [
            record
            for record in processed_records
            if (
                (rtype is None or record["type"] == rtype)
                and (name is None or record["name"] == self._full_name(name))
                and (content is None or record["content"] == content)
            )
        ]

        LOGGER.debug("list_records: %s", filtered_records)
        return filtered_records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier:
            identifier = self._get_record_identifier(rtype=rtype, name=name)

        params = {"id": identifier, "domain": self.domain, "content": content}
        result = self._api_call("edit-record", params)

        LOGGER.debug("update_record: %s", result)
        return result

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier:
            identifier = self._get_record_identifier(
                rtype=rtype, name=name, content=content
            )

        params = {"domain": self.domain, "id": identifier}
        self._api_call("remove-record", params)

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _api_call(self, method, params):
        if self._get_provider_option("auth_token") is None:
            raise Exception("Must provide API token")

        data = {"method": method, "params": params}
        response = self._request("POST", "", data)

        if "error" in response.keys():
            error = response["error"]
            raise Exception("%d: %s" % (error["code"], error["message"]))

        return response["result"]

    def _get_record_identifier(self, rtype=None, name=None, content=None):
        records = self._list_records(rtype=rtype, name=name, content=content)
        if len(records) == 1:
            return records[0]["id"]

        raise Exception("Unambiguous record could not be found.")

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        token = self._get_provider_option("auth_token")
        headers = {
            "Authorization": "Njalla " + token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        response = requests.request(
            action,
            self.api_endpoint + url,
            headers=headers,
            params=query_params,
            json=data,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()
