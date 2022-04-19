"""Module provider for hostingde (Hosting.de)"""
import json
import logging
import time

import requests

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["hosting.de"]

# be aware to provide an auth_token
# LEXICON_HOSTINGDE_AUTH_TOKEN


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument("--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):
    """Provider class for Hosting"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://secure.hosting.de/api/dns/v1/json"

    def _authenticate(self):

        response = self._get_zone_config()

        LOGGER.debug("authenticate debug: %s", response)
        if response == []:
            raise Exception(f"Domain {self.domain} not found")

        self.domain_id = response.get("id", None)

    # Helper
    def _get_zone_config(self):

        data = {"filter": {"field": "ZoneName", "value": self.domain}}
        response = self._request(action="POST", url="/zoneConfigsFind", data=data)
        if response != []:
            return response[0]

        return []

    # Normal Behaviour List all records. If filters are provided, send to the API if possible,
    # else apply filter locally. Return value should be a list of records.
    # Return an empty list if no records found
    # type, name and content are used to filter records.
    # caused the fact, that provider will enclose TXT values with ""
    # we have filter content afterwords
    def _list_records(self, rtype=None, name=None, content=None):
        data = {}
        subfilter = []  # used by API to filter
        subfilter.append({"field": "zoneConfigId", "value": self.domain_id})
        if rtype:
            subfilter.append({"field": "RecordType", "value": rtype})
        if name:
            subfilter.append({"field": "RecordName", "value": self._full_name(name)})
        if subfilter:
            data.update(
                {"filter": {"subFilterConnective": "AND", "subFilter": subfilter}}
            )

        LOGGER.debug("list_records filter: %s", data)
        raw_records = self._request(action="POST", url="/recordsFind", data=data)

        processed_records = []

        for record in raw_records:
            processed_record = {
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "id": record["id"],
                "content": record["content"],
            }
            if record["priority"]:
                processed_record["priority"] = record["priority"]
            processed_record = self._clean_TXT_record(processed_record)

            processed_records.append(processed_record)

        if content:
            processed_records = [
                record
                for record in processed_records
                if record["content"].lower() == content.lower()
            ]

        LOGGER.debug("list_records: %s", processed_records)
        return processed_records

    # Normal Behavior Create a new DNS record. Return a boolean True if successful.
    # If Record Already Exists Do nothing. DO NOT throw exception.
    # TTL If not specified or set to 0, use reasonable default.
    def _create_record(self, rtype, name, content):
        records = self._list_records(rtype, name, content)
        if records:
            LOGGER.debug("not creating duplicate record: %s", records[0])
            return True

        zone_config = self._get_zone_config()
        priority = self._get_lexicon_option("priority")
        ttl = self._get_lexicon_option("ttl")

        record = {"name": self._full_name(name), "type": rtype, "content": content}
        if ttl:
            if int(ttl) < 60:
                LOGGER.warning("ttl must be minimum 60")
                ttl = 60
            record["ttl"] = int(ttl)
        if priority:
            record["priority"] = int(priority)

        LOGGER.debug("create_record: %s", record)
        data = {"zoneConfig": zone_config, "recordsToAdd": [record]}

        self._request(action="POST", url="/zoneUpdate", data=data)
        return True

    # Normal Behaviour Update a record. Record to be updated can be specified by providing id OR
    # name, type and content. Return a boolean
    # True if successful.
    # TTL:
    #    If not specified, do not modify ttl.
    #    If set to 0, reset to reasonable default.
    # No Match Throw exception?
    # Update a record. use delete & create cause there is no API update call
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier:
            records = self._list_records()
            records = [r for r in records if r["id"] == identifier]
        else:
            records = self._list_records(rtype, name, None)

        if not records:
            raise Exception("Record not found")
        if len(records) > 1:
            raise Exception("Record not unique")
        orig_record = records[0]
        orig_id = orig_record["id"]

        new_rtype = rtype if rtype else orig_record["type"]
        new_name = name if name else orig_record["name"]
        new_content = content if content else orig_record["content"]

        self._delete_record(orig_id)
        return self._create_record(new_rtype, new_name, new_content)

    # Normal Behaviour Remove a record. Record to be deleted can be
    # specified by providing id OR name, type and content.
    # Return a boolean True if successful.
    # No Match Do nothing. DO NOT throw exception
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids.append(identifier)

        LOGGER.debug("delete_records: %s", delete_record_ids)
        records = []
        for record_id in delete_record_ids:
            records.append({"id": record_id})

        zone_config = self._get_zone_config()
        data = {"zoneConfig": zone_config, "recordsToDelete": records}

        self._request(action="POST", url="/zoneUpdate", data=data)

        # sometimes it takes some time to delete a record
        # so, here check after deleting and loop
        # if record(s) is not deleted after 30 seconds > False
        retries = 30
        for record_id in delete_record_ids:
            while True:
                if self._list_records(record_id):
                    if retries < 1:
                        break
                    retries = retries - 1
                    time.sleep(1)
                else:
                    break

        LOGGER.debug("delete_records: %s", retries > 0)
        return retries > 0

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        data.update({"authToken": self._get_provider_option("auth_token")})

        read_page = 1
        return_data = []
        retries = 30

        # in some situatons, API uses pagination
        # here we check and if there is pagination, go through all pages
        while True:
            page_data = data
            page_data.update({"page": read_page})

            response = requests.request(
                action,
                self.api_endpoint + url,
                params=query_params,
                data=json.dumps(page_data),
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            response_json = response.json()  # Work with json Object
            LOGGER.debug("_request response: %s", response_json)
            status = response_json.get("status", "*** no status available ***")
            # if API still busy just wait and retry
            if (
                status == "error"
                and response_json.get("errors")[0].get("value", "") == "blocked"
            ):
                if retries < 1:
                    raise Exception(f"Api error: {response_json.get('errors')}")
                retries = retries - 1
                time.sleep(1)
                continue

            if status not in ("success", "pending"):
                raise Exception(f"Api error: {response_json.get('errors')}")
            # check if there a data object
            read_data = response_json.get("response", {}).get("data", None)

            # if no data object, check if there a records object
            if read_data is None:
                read_data = response_json.get("response", {}).get("records", None)

            # add response data to return data
            if read_data:
                return_data += read_data

            # is there pagination and more data available?
            total_pages = response_json.get("response", {}).get("totalPages", 0)
            if total_pages in (read_page, 0):
                break  # no more data

            read_page = read_page + 1

        return return_data
