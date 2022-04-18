"""Module provider for Dinahosting"""
# import re
import hashlib
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["dinahosting.com"]

# These record types are either not supported by the API or are non-compliant
UNSUPPORTED_TYPES = ["MX", "SRV", "NS", "SOA", "LOC"]

# The API returns the record's content in any of these keys
CONTENT_KEYS = ["ip", "address", "text", "destinationHostname"]

# The API returns the record's name in any of these keys
NAME_KEYS = ["host", "hostname"]

# API response codes
RC_SUCCESS = 1000
RC_SUCCESS_PENDING = 1001
RC_UNKNOWN_COMMAND = 2000
RC_COMMAND_SYNTAX_ERROR = 2001
RC_COMMAND_USE_ERROR = 2002
RC_PARAM_MISSING = 2003
RC_PARAM_VALUE_RANGE = 2004
RC_PARAM_VALUE_SYNTAX = 2005
RC_AUTH_ERROR_USER = 2200
RC_AUTH_ERROR_OBJECT = 2201
RC_OBJECT_EXISTS = 2302
RC_OBJECT_NOT_EXISTS = 2303
RC_COMMAND_FAILED = 2400
RC_COMMAND_FAILED_FATAL = 2500
RC_COMMAND_TIMEOUT = 2501


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )


class Provider(BaseProvider):
    """Provider class for Dinahosting"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://dinahosting.com/special/api.php"

    def _authenticate(self):
        data = {"command": "Services_GetDomains"}
        payload = self._post("", data)

        if not payload["data"]:
            raise AuthenticationError("No domain found")

        for data in payload["data"]:
            if data["domain"] == self.domain:
                break
        else:
            raise AuthenticationError("Requested domain is not among the owned domains")

        self.domain_id = self.domain

    def _create_record(self, rtype, name, content):
        Provider._check_unsupported_type(rtype)

        rel_name = self._relative_name(name)
        data = {"domain": self.domain, "hostname": rel_name}

        if rtype == "A":
            data["command"] = "Domain_Zone_AddTypeA"
            data["ip"] = content
        elif rtype == "AAAA":
            data["command"] = "Domain_Zone_AddTypeAAAA"
            data["ip"] = content
        elif rtype == "CNAME":
            data["command"] = "Domain_Zone_AddTypeCname"
            data["destinationHostname"] = content
        elif rtype == "TXT":
            data["command"] = "Domain_Zone_AddTypeTXT"
            data["text"] = content

        try:
            self._post("", data)
        except requests.exceptions.HTTPError as err:
            already_exists = (
                err.response.json()["responseCode"] == RC_OBJECT_EXISTS
            ) or (err.response.json()["responseCode"] == RC_COMMAND_FAILED)
            if not already_exists:
                raise

        LOGGER.debug("create_record: %s", True)
        return True

    def _list_records(self, rtype=None, name=None, content=None):
        if rtype:
            formatted_rtype = "Cname" if rtype == "CNAME" else rtype
            data = {
                "command": f"Domain_Zone_GetType{formatted_rtype}",
                "domain": self.domain,
            }
        else:
            data = {"command": "Domain_Zone_GetAll", "domain": self.domain}

        payload = self._post("", data)

        records = []
        for record in payload["data"]:
            precord = self._parse_record(record)
            ptype = rtype if rtype else precord["type"]

            if name and name not in precord["name_variants"]:
                continue

            if content and content != precord["content"]:
                continue

            if rtype and precord["type"] and rtype != precord["type"]:
                continue

            processed_record = {
                "type": ptype,
                "name": precord["name_variants"][0],
                "content": precord["content"],
                "ttl": None,  # The API does not expose the record's ttl
            }
            processed_record["id"] = Provider._identifier(processed_record)
            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier:
            records = self._list_records()
            matching_records = [
                record for record in records if record["id"] == identifier
            ]
        else:
            matching_records = self._list_records(rtype, name)

        # Check if record exists, otherwise raise an error
        if not matching_records:
            raise Exception("No matching records found. Cannot update.")
        if len(matching_records) > 1:
            raise Exception("Multiple matching records found. Cannot update.")

        record = matching_records[0]
        # The API does not offer update functions for most of the record types
        delete_result = self._delete_record(
            identifier, record["type"], record["name"], record["content"]
        )
        create_result = self._create_record(rtype, name, content)

        LOGGER.debug("update_record: %s", (delete_result and create_result))
        return delete_result and create_result

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            records = self._list_records()
            delete_records = [
                record for record in records if record["id"] == identifier
            ]
        else:
            delete_records = self._list_records(rtype, name, content)

        for delete_record in delete_records:
            ptype = rtype if rtype else delete_record["type"]
            Provider._check_unsupported_type(ptype)

            rel_name = self._relative_name(delete_record["name"])
            data = {"domain": self.domain, "hostname": rel_name}

            if ptype == "A":
                data["command"] = "Domain_Zone_DeleteTypeA"
                data["ip"] = delete_record["content"]
            elif ptype == "AAAA":
                data["command"] = "Domain_Zone_DeleteTypeAAAA"
                data["ip"] = delete_record["content"]
            elif ptype == "CNAME":
                data["command"] = "Domain_Zone_DeleteTypeCname"
            elif ptype == "TXT":
                data["command"] = "Domain_Zone_DeleteTypeTXT"
                data["text"] = delete_record["content"]

            try:

                self._post("", data)
            except requests.exceptions.HTTPError as err:
                not_exists = err.response.json()["responseCode"] == RC_OBJECT_NOT_EXISTS
                if not not_exists:
                    raise

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        # All requests are POST. Query parameters are not used.
        query_params = {}

        if data is None:
            data = {}
        data["responseType"] = "Json"

        username = self._get_provider_option("auth_username")
        password = self._get_provider_option("auth_password")
        response = requests.request(
            action,
            self.api_endpoint + url,
            auth=(username, password),
            params=query_params,
            data=data,
        )
        # If the request fails for any reason, throw an error.
        response.raise_for_status()

        rjson = response.json()
        if int(rjson["responseCode"]) != RC_SUCCESS:
            api_error_message = "%s API Error for url: %s" % (
                rjson["responseCode"],
                response.url,
            )
            raise requests.exceptions.HTTPError(api_error_message, response=response)
        return rjson

    def _parse_record(self, record):
        parsed_record = {}
        parsed_record["type"] = Provider._parse_record_type(record)
        parsed_record["content"] = Provider._find_matching_record_value(
            CONTENT_KEYS, record
        )
        raw_name = Provider._find_matching_record_value(NAME_KEYS, record)
        fqdn_name = self._fqdn_name(raw_name)
        full_name = self._full_name(raw_name)
        parsed_record["name_variants"] = [full_name, fqdn_name, raw_name]

        return parsed_record

    @staticmethod
    def _identifier(record):
        md5 = hashlib.md5()
        md5.update((record.get("type", "")).encode("utf-8"))
        md5.update((record.get("name", "")).encode("utf-8"))
        md5.update((record.get("data", "")).encode("utf-8"))
        return md5.hexdigest()

    @staticmethod
    def _find_matching_record_value(keys, record):
        if record is None or keys is None:
            return None

        matched_value = None
        for key in keys:
            if key in record:
                matched_value = record[key]
                break
        return matched_value

    @staticmethod
    def _parse_record_type(record):
        if not record or "type" not in record:
            return None
        if record["type"].startswith("MX"):
            return "MX"
        return record["type"]

    @staticmethod
    def _check_unsupported_type(rtype):
        if rtype in UNSUPPORTED_TYPES:
            raise Exception(f"Record type {rtype} is not supported by the API")
