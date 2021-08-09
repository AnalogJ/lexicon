"""Module provider for Gehirn"""
import base64
import json
import logging
import re

import requests
from requests.auth import HTTPBasicAuth

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["gehirn.jp"]


def provider_parser(subparser):
    """Construct subparser for Gehirn"""
    subparser.add_argument(
        "--auth-token", help="specify access token for authentication"
    )
    subparser.add_argument(
        "--auth-secret", help="specify access secret for authentication"
    )


BUILD_FORMATS = {
    "A": "{address}",
    "AAAA": "{address}",
    "CNAME": "{cname}",
    "TXT": "{data}",
    "NS": "{nsdname}",
    "MX": "{prio} {exchange}",
    "SRV": "{prio} {weight} {port} {target}",
}

FORMAT_RE = {
    "A": re.compile(r"(?P<address>.+)"),
    "AAAA": re.compile(r"(?P<address>.+)"),
    "CNAME": re.compile(r"(?P<cname>.+)"),
    "TXT": re.compile(r"(?P<data>.+)"),
    "NS": re.compile(r"(?P<nsdname>.+)"),
    "MX": re.compile(r"(?P<prio>\d+)\s+(?P<exchange>.+)"),
    "SRV": re.compile(
        r"(?P<prio>\d+)\s+(?P<weight>\d+)\s+(?P<port>\d+)\s+(?P<target>.+)"
    ),
}


class Provider(BaseProvider):
    """Provider class for Gehirn"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.version_id = None
        self.api_endpoint = "https://api.gis.gehirn.jp/dns/v1"

    def _authenticate(self):
        payload = self._get("/zones")

        domains = [item for item in payload if item["name"] == self.domain]
        if not domains:
            raise AuthenticationError("No domain found")

        self.domain_id = domains[0]["id"]
        self.version_id = domains[0]["current_version_id"]

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        name = self._full_name(name)
        a_record = self._parse_content(rtype, content)

        record = None
        records = self._get_records(rtype=rtype, name=name)
        if not records:
            record = {
                "type": rtype,
                "name": name,
                "enable_alias": False,
                "ttl": self._get_lexicon_option("ttl"),
                "records": [],
            }
        else:
            record = records[0]

        if a_record in record["records"]:
            LOGGER.debug("create_record: %s", True)
            return True

        record["records"].append(a_record)
        self._update_internal_record(record)
        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        records = []
        if name:
            name = self._full_name(name)
        for record in self._get_records(rtype=rtype, name=name):
            for a_record in record["records"]:
                content = self._build_content(record["type"], a_record)
                processed_record = {
                    "type": record["type"],
                    "name": record["name"].rstrip("."),
                    "ttl": record["ttl"],
                    "content": content,
                    "id": f"{record['id']}.{base64.b64encode(content.encode('utf-8')).decode('ascii')}",
                }
                self._parse_content(record["type"], processed_record["content"])
                records.append(processed_record)

        if content:
            records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def _update_record(self, identifier=None, rtype=None, name=None, content=None):

        if name:
            name = self._full_name(name)

        if not identifier:
            if not (rtype and name and content):
                raise Exception("type, name and content must be specified.")

            records = self._get_records(rtype=rtype, name=name)

            if not records:
                self._create_record(rtype=rtype, name=name, content=content)
                LOGGER.debug("update_record: %s", True)
                return True

            record = {
                "id": records[0]["id"],
                "type": rtype,
                "name": name,
                "enable_alias": False,
                "ttl": self._get_lexicon_option("ttl"),
                "records": [self._parse_content(rtype, content)],
            }

        else:
            # with identifier
            records = self._get_records(identifier=identifier)
            if not records:
                raise Exception("Record identifier could not be found.")

            record = records[0]

            if "." in identifier:
                # modify single record
                self._delete_record(identifier=identifier)
                self._create_record(
                    rtype=rtype or record["type"],
                    name=name or record["name"],
                    content=content,
                )
                LOGGER.debug("update_record: %s", True)
                return True
            # update entire record
            if rtype:
                record["type"] = rtype
            if name:
                record["name"] = name
            record["ttl"] = self._get_lexicon_option("ttl")
            if content:
                record["records"] = [self._parse_content(record["type"], content)]

        self._update_internal_record(record)
        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            if "." not in identifier:
                # delete entire record
                path = f"/zones/{self.domain_id}/versions/{self.version_id}/records/{identifier}"
                self._delete(path)
                LOGGER.debug("delete_record: %s", True)
                return True

            record_identifier = identifier.split(".")[1]

            records = self._get_records(identifier=identifier)
            if not records:
                raise Exception("Record identifier could not be found.")

            record = records[0]
            for index, a_record in enumerate(record["records"]):
                target_content = self._build_content(record["type"], a_record)
                target_identifier = base64.b64encode(
                    target_content.encode("utf-8")
                ).decode("ascii")

                if target_identifier == record_identifier:
                    del record["records"][index]
                if not record["records"]:
                    # delete entire record
                    path = f"/zones/{self.domain_id}/versions/{self.version_id}/records/{record['id']}"
                    self._delete(path)
                else:
                    self._update_internal_record(record)

                LOGGER.debug("delete_record: %s", True)
                return True

            raise Exception("Record identifier could not be found.")

        record = None
        if name is not None:
            name = self._full_name(name)
        if content is not None:
            content = self._bind_format_target(rtype, content)
            record = self._parse_content(rtype, content)

        records = self._get_records(rtype=rtype, name=name)

        for a_record in records:
            if record and record in a_record["records"]:
                a_record["records"].remove(record)
                if a_record["records"]:
                    self._update_internal_record(a_record)
                    continue

            path = f"/zones/{self.domain_id}/versions/{self.version_id}/records/{a_record['id']}"
            self._delete(path)

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _full_name(self, record_name):
        record_name = super(Provider, self)._full_name(record_name)
        if not record_name.endswith("."):
            record_name += "."
        return record_name

    def _bind_format_target(self, rtype, target):
        if rtype == "CNAME" and not target.endswith("."):
            target += "."
        return target

    def _filter_records(self, records, identifier=None, rtype=None, name=None):
        filtered_records = []

        if identifier:
            identifier = identifier.split(".")[0]

        for record in records:
            if rtype and record["type"] != rtype:
                continue
            if name and record["name"] != name:
                continue
            if identifier and record["id"] != identifier:
                continue
            filtered_records.append(record)
        return filtered_records

    def _get_records(self, identifier=None, rtype=None, name=None):
        path = f"/zones/{self.domain_id}/versions/{self.version_id}/records"
        return self._filter_records(
            self._get(path), identifier=identifier, rtype=rtype, name=name
        )

    def _update_internal_record(self, record):
        if record.get("id"):
            # PUT
            path = f"/zones/{self.domain_id}/versions/{self.version_id}/records/{record['id']}"
            return self._put(path, record)

        # POST
        path = f"/zones/{self.domain_id}/versions/{self.version_id}/records"
        return self._post(path, record)

    def _build_content(self, rtype, record):
        return BUILD_FORMATS[rtype].format(**record)

    def _parse_content(self, rtype, content):
        return FORMAT_RE[rtype].match(content).groupdict()

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
            data=json.dumps(data) if data else None,
            headers=default_headers,
            auth=default_auth,
        )
        try:
            # if the request fails for any reason, throw an error.
            response.raise_for_status()
        except BaseException:
            LOGGER.error(response.text)
            raise
        return response.json()
