"""Module provider for Sakura Cloud"""
import json
import logging

import requests
from requests.auth import HTTPBasicAuth

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["sakura.ne.jp"]


def provider_parser(subparser):
    """Generate a provider parser for Sakura Cloud"""
    subparser.add_argument(
        "--auth-token", help="specify access token for authentication"
    )
    subparser.add_argument(
        "--auth-secret", help="specify access secret for authentication"
    )


class Provider(BaseProvider):
    """Provider class for Sakura Cloud"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://secure.sakura.ad.jp/cloud/zone/is1a/api/cloud/1.1"

    def _authenticate(self):

        query_params = {"Filter": {"Provider.Class": "dns", "Name": self.domain}}
        payload = self._get("/commonserviceitem", query_params=query_params)

        for item in payload["CommonServiceItems"]:
            if item["Status"]["Zone"] == self.domain:
                self.domain_id = item["ID"]
                return

        raise AuthenticationError("No domain found")

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        name = self._relative_name(name)
        resource_record_sets = self._get_resource_record_sets()
        index = self._find_resource_record_set(
            resource_record_sets, rtype=rtype, name=name, content=content
        )
        if index >= 0:
            LOGGER.debug("create_record: %s", False)
            return False

        resource_record_sets.append(
            {
                "Name": name,
                "Type": rtype,
                "RData": self._bind_format_target(rtype, content),
                "TTL": self._get_lexicon_option("ttl"),
            }
        )

        self._update_resource_record_sets(resource_record_sets)
        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        records = []

        for record in self._get_resource_record_sets():
            processed_record = {
                "type": record["Type"],
                "name": self._full_name(record["Name"]),
                "ttl": record["TTL"],
                "content": record["RData"],
                # 'id': None,
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
    def _update_record(self, identifier=None, rtype=None, name=None, content=None):

        if not (rtype and name and content):
            raise Exception("rtype ,name and content must be specified.")

        name = self._relative_name(name)
        resource_record_sets = self._get_resource_record_sets()
        index = self._find_resource_record_set(
            resource_record_sets, rtype=rtype, name=name
        )

        if index >= 0:
            resource_record_sets[index]["Type"] = rtype
            resource_record_sets[index]["Name"] = name
            resource_record_sets[index]["RData"] = self._bind_format_target(
                rtype, content
            )
            resource_record_sets[index]["TTL"] = self._get_lexicon_option("ttl")
        else:
            resource_record_sets.append(
                {
                    "Name": name,
                    "Type": rtype,
                    "RData": self._bind_format_target(rtype, content),
                    "TTL": self._get_lexicon_option("ttl"),
                }
            )

        self._update_resource_record_sets(resource_record_sets)
        LOGGER.debug("create_record")

        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        resource_record_sets = self._get_resource_record_sets()

        if name is not None:
            name = self._relative_name(name)
        if content is not None:
            content = self._bind_format_target(rtype, content)

        filtered_records = []
        for record in resource_record_sets:
            if rtype and record["Type"] != rtype:
                continue
            if name and record["Name"] != name:
                continue
            if content and record["RData"] != content:
                continue
            filtered_records.append(record)

        if not filtered_records:
            LOGGER.debug("delete_record: %s", False)
            return False

        for record in filtered_records:
            resource_record_sets.remove(record)

        self._update_resource_record_sets(resource_record_sets)
        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _full_name(self, record_name):
        if record_name == "@":
            record_name = self.domain
        return super(Provider, self)._full_name(record_name)

    def _relative_name(self, record_name):
        name = super(Provider, self)._relative_name(record_name)
        if not name:
            name = "@"
        return name

    def _bind_format_target(self, rtype, target):
        if rtype == "CNAME" and not target.endswith("."):
            target += "."
        return target

    def _find_resource_record_set(self, records, rtype=None, name=None, content=None):
        for index, record in enumerate(records):
            if rtype and record["Type"] != rtype:
                continue
            if name and record["Name"] != name:
                continue
            if content and record["RData"] != content:
                continue
            return index
        return -1

    def _get_resource_record_sets(self):
        payload = self._get(f"/commonserviceitem/{self.domain_id}")
        return payload["CommonServiceItem"]["Settings"]["DNS"]["ResourceRecordSets"]

    def _update_resource_record_sets(self, resource_record_sets):
        content = {
            "CommonServiceItem": {
                "Settings": {"DNS": {"ResourceRecordSets": resource_record_sets}}
            }
        }
        return self._put(f"/commonserviceitem/{self.domain_id}", content)

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        default_auth = HTTPBasicAuth(
            self._get_provider_option("auth_token"),
            self._get_provider_option("auth_secret"),
        )

        query_string = ""
        if query_params:
            query_string = json.dumps(query_params)

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_string,
            data=json.dumps(data),
            headers=default_headers,
            auth=default_auth,
        )
        try:
            # if the request fails for any reason, throw an error.
            response.raise_for_status()
        except BaseException:
            LOGGER.error(response.json().get("error_msg"))
            raise
        return response.json()
