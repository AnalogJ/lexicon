"""
Module provider for EUserv

Author: Matthias Schoettle (@mschoettle), 2019

EUserv API Docs: https://support.euserv.com/api-doc/
"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["euserv.com"]

# Success response code
RC_SUCCESS = 100

API_ENDPOINT = "https://support.euserv.com/"

# Product group ID for domains
PRODUCT_ID_DOMAIN = 1


def provider_parser(subparser):
    """Configure provider parser for Euserv"""
    subparser.add_argument(
        "--auth-username", help="specify email address for authentication"
    )
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )


class Provider(BaseProvider):
    """Provider class for Euserv"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = API_ENDPOINT
        # Order ID for the domain
        self.order_id = None
        self.domain_id = None
        self.session_id = None

    def _authenticate(self):
        if not (
            self._get_provider_option("auth_username")
            and self._get_provider_option("auth_password")
        ):
            raise ValueError(
                "username and password must be specified, add --help for details"
            )

        # Get a session ID first.
        LOGGER.info("Getting Session ID...")
        response = self._get()
        self.session_id = response["result"]["sess_id"]["value"]

        LOGGER.info("Logging in...")
        auth_response = self._get(
            query_params={
                "subaction": "login",
                "email": self._get_provider_option("auth_username"),
                "password": self._get_provider_option("auth_password"),
            }
        )

        # Find the contract number of the given domain
        orders = auth_response["result"]["orders"]

        for order in orders:
            if int(order["pg_id"]["value"]) == PRODUCT_ID_DOMAIN:
                # The description contains the description of the product itself
                # and in a second line the domain name
                order_description = order["ord_description"]["value"].split("\n")

                if order_description[1] == self.domain:
                    self.order_id = order["ord_no"]["value"]
                    break
        else:
            raise AuthenticationError("Order for domain not found")

        # Select the order for the given domain so we can use the DNS actions
        LOGGER.info("Choosing order %s", self.order_id)
        self._get(query_params={"subaction": "choose_order", "ord_no": self.order_id})

        # Retrieve domain ID
        LOGGER.info("Retrieving DNS records to find domain id for %s...", self.domain)
        domains = self._get(query_params={"subaction": "kc2_domain_dns_get_records"})

        for domain in domains["result"]["domains"]:
            if domain["dom_domain"]["value"] == self.domain:
                self.domain_id = domain["dom_id"]["value"]
                break
        else:
            raise AuthenticationError("Domain not found in DNS records")

    def _create_record(self, rtype, name, content):
        records = self._list_records(rtype, name, content)

        if records:
            LOGGER.debug("record already exists: %s", records[0])
            return True

        query_params = {
            "subaction": "kc2_domain_dns_set",
            "dom_id": self.domain_id,
            "type": rtype,
            "content": content,
        }

        if name:
            query_params["subdomain"] = self._subdomain_name(name)

        self._add_ttl(query_params)
        self._add_priority(query_params)

        response = self._get(query_params=query_params)
        LOGGER.debug("create_record response: %s", response)

        return True

    def _list_records(self, rtype=None, name=None, content=None):
        LOGGER.info(
            "Listing records for type=%s, name=%s, content=%s", rtype, name, content
        )

        query_params = {
            "subaction": "kc2_domain_dns_get_records",
            "dns_records_load_only_for_dom_id": self.domain_id,
        }

        if rtype:
            query_params["dns_records_load_type"] = rtype

        if name:
            query_params["dns_records_load_subdomain"] = self._subdomain_name(name)

        if content:
            query_params["dns_records_load_content"] = content

        payload = self._get(query_params=query_params)

        response = payload["result"]["domains"][0]

        LOGGER.debug("list_records raw response: %s", response)

        records = []

        if "dns_records" in response:
            for record in response["dns_records"]:
                processed_record = {
                    "type": record["type"]["value"],
                    "name": record["name"]["value"],
                    "ttl": record["ttl"]["value"],
                    "content": record["content"]["value"],
                    "id": record["id"]["value"],
                    "priority": record["prio"]["value"],
                }

                records.append(processed_record)

        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier is None:
            LOGGER.info("No identifier for record provided, trying to find it...")
            identifier = self._find_record_identifier(rtype, name, None)

        query_params = {"subaction": "kc2_domain_dns_set", "dns_record_id": identifier}

        if rtype:
            query_params["type"] = rtype

        if name:
            query_params["subdomain"] = self._subdomain_name(name)

        if content:
            query_params["content"] = content

        self._add_ttl(query_params)
        self._add_priority(query_params)

        response = self._get(query_params=query_params)
        LOGGER.debug("update_record: %s", response)

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        record_ids = []

        if identifier is None:
            LOGGER.info("No identifier for record provided, trying to find it...")
            records = self._list_records(rtype, name, content)
            record_ids = [record["id"] for record in records]
        else:
            record_ids.append(identifier)

        LOGGER.debug("record IDs to be deleted: %s", record_ids)

        for record_id in record_ids:
            query_params = {
                "subaction": "kc2_domain_dns_remove",
                "dns_record_id": record_id,
            }

            response = response = self._get(query_params=query_params)
            LOGGER.debug("delete_record: %s", response)

        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        query_params["method"] = "json"

        if self.session_id:
            query_params["sess_id"] = self.session_id

        response = requests.request(
            action,
            self.api_endpoint,
            params=query_params,
            data=json.dumps(data),
            headers={"Content-Type": "application/json; charset=utf-8"},
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()

        response_json = response.json()

        if int(response_json["code"]) != RC_SUCCESS:
            raise Exception(
                f"Error {response_json['code']} in request: {response_json['message']}"
            )

        return response_json

    # Adds TTL parameter if passed as argument to lexicon.
    def _add_ttl(self, data):
        if self._get_lexicon_option("ttl"):
            data["ttl"] = int(self._get_lexicon_option("ttl"))

    # Adds priority parameter if passed as argument to lexicon.
    def _add_priority(self, data):
        if self._get_lexicon_option("priority"):
            data["prio"] = int(self._get_lexicon_option("priority"))

    # Find identifier of a record with the given properties.
    def _find_record_identifier(self, rtype, name, content):
        records = self._list_records(rtype, name, content)

        LOGGER.debug("records: %s", records)

        if len(records) == 1:
            return records[0]["id"]

        raise Exception("No record identifier found")

    # Get the subdomain name only for the given name.
    # This provider automatically suffixes the name with the domain name.
    def _subdomain_name(self, name):
        subdomain = self._full_name(name)
        domain_suffix = "." + self.domain

        # Remove domain name since it will be automatically added by the provider
        if subdomain.endswith(domain_suffix):
            subdomain = subdomain[: len(subdomain) - len(domain_suffix)]

        return subdomain
