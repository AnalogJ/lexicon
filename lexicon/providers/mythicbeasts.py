"""Module provider for Mythic Beasts"""
from __future__ import absolute_import

import json
import logging

import requests

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["mythic-beasts.com"]


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.description = """
        There are two ways to provide an authentication granting access to the Mythic Beasts API
        1 - With your API credentials (user/password),
            with --auth-username and --auth-password flags.
        2 - With an API token, using --auth-token flags.
        These credentials and tokens must be generated using the Mythic Beasts API v2.
    """
    subparser.add_argument(
        "--auth-username",
        help="specify API credentials username",
    )
    subparser.add_argument(
        "--auth-password",
        help="specify API credentials password",
    )
    subparser.add_argument(
        "--auth-token",
        help="specify API token for authentication",
    )
    subparser.add_argument(
        "--zone-id",
        help="specify the zone id (if set, API token can be scoped to the target zone)",
    )
    


class Provider(BaseProvider):
    """Provider class for Cloudflare"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.mythic-beasts.com/dns/v2"
        self.auth_token = None

    def _authenticate(self):
        zone_id = self._get_provider_option("zone_id")
        if not zone_id:
            payload = self._get("/zones")

            if not payload["zones"]:
                raise Exception("No domain found")
            if len(payload["zones"]) > 1:
                raise Exception("Too many domains found. This should not happen")

            self.domain_id = payload["zones"][0]
        else:
            payload = self._get("/zones")
            if (zone_id not in payload["zones"]):
                raise Exception("Zone id not found")

            self.domain_id = zone_id

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        # content, cf_data = self._format_content(rtype, content)
        LOGGER.debug("type %s",rtype)
        LOGGER.debug("name %s",name)
        LOGGER.debug("content %s",content)
        LOGGER.debug("cf_data %s",cf_data)
        data = {
            "records": [{
                "host": self._full_name(name),
                "type": rtype,
                "data": content,
            }]
        }
        if self._get_lexicon_option("ttl"):
            data["records"][0]["ttl"] = self._get_lexicon_option("ttl")

        payload = {"success": True}
        try:
            payload = self._post(f"/zones/{self.domain_id}/records", data)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code != 400:
                raise

        LOGGER.debug("create_record: %s", payload["message"])
        return payload["message"]

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        filter_obj = {}
        if rtype:
            filter_obj["type"] = rtype
        if name:
            filter_obj["host"] = self._full_name(name)
        if content:
            filter_obj["data"] = content
        
        records = []
        
        payload = self._get(f"/zones/{self.domain_id}/records", filter_obj)

        LOGGER.debug("payload: %s", payload)

        for record in payload["records"]:
            processed_record = {
                "type": record["type"],
                "name": record["host"],
                "ttl": record["ttl"],
                "content": record["data"],
            }
            if(record["type"]=='MX' and record["mx_priority"]):
                processed_record["options"]= {"mx": {"priority": record["mx_priority"]}}

            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        LOGGER.debug("Number of records retrieved: %d", len(records))
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier is None:
            records = self._list_records(rtype, name)
            if len(records) == 1:
                name = records[0]["name"]
                rtype = records[0]["type"]
            elif len(records) < 1:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )

        data = {"records":[{}]}
        # if rtype:
        #     data["type"] = rtype
        # if name:
        #     data["host"] = self._full_name(name)
        if content:
            data["records"][0]["data"] = content
        if self._get_lexicon_option("ttl"):
            data["records"][0]["ttl"] = self._get_lexicon_option("ttl")

        LOGGER.debug(data)

        payload = self._put(f"/zones/{self.domain_id}/records/{name}/{rtype}", data)

        LOGGER.debug("update_record: %s", payload["message"])
        return payload["message"]

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        records = self._list_records(rtype, name, content)

        for record in records:
            LOGGER.debug("delete_records: %s", record)
            name = record["name"]
            rtype = record["type"]
            self._delete(f"/zones/{self.domain_id}/records/{name}/{rtype}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        # may need to get auth token
        if self.auth_token is None and self._get_provider_option('auth_token') is None:
            auth_request = requests.request(
             "POST",
             "https://auth.mythic-beasts.com/login",
             data={
                 "grant_type": "client_credentials"
             },
             auth=(self._get_provider_option("auth_username"),self._get_provider_option("auth_password"))
            )

            auth_request.raise_for_status()
            post_result = auth_request.json()

            if not post_result["access_token"]:
                raise Exception(
                    "Error, could not get access token "
                    f"for Mythic Beasts API for user: {self._get_provider_option('auth_email')}"
                )

            self.auth_token = post_result["access_token"]
        elif self.auth_token is None:
            self.auth_token = self._get_provider_option('auth_token')

        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {self.auth_token}"
        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    def _format_content(self, rtype, content):
        """
        Special case handling from some record types that Cloudflare needs
        formatted differently

        Returns new values for the content and data properties to be sent
        on the request
        """
        data = None
        if rtype == "SSHFP":
            # For some reason the CloudFlare API does not let you set content
            # directly when creating an SSHFP record. You need to pass the
            # fields that make up the record seperately, then the API joins
            # them back together
            _fp = content.split(" ")
            data = {"algorithm": _fp[0], "type": _fp[1], "fingerprint": _fp[2]}
            content = None

        return content, data
