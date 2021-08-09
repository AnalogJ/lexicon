"""Module provider for Netcup"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["netcup.de"]


def provider_parser(subparser):
    """Configure provider parser for Netcup"""
    subparser.add_argument(
        "--auth-customer-id", help="specify customer number for authentication"
    )
    subparser.add_argument("--auth-api-key", help="specify API key for authentication")
    subparser.add_argument(
        "--auth-api-password", help="specify API password for authentication"
    )


class Provider(BaseProvider):
    """Provider class for Netcup"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = 0
        self.zone_ttl = None
        self.api_session_id = None
        self.api_endpoint = (
            self._get_provider_option("api_endpoint")
            or "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"
        )

    # lexicon.provider.Provider overrides:

    def _authenticate(self):
        """Authenticate with netcup server. Must be called first."""
        login_info = self._apicall("login")
        self.api_session_id = login_info["apisessionid"]
        if not self.api_session_id:
            raise AuthenticationError("Login failed")
        # query ttl and verify access to self.domain:
        zone_info = self._apicall("infoDnsZone", domainname=self.domain)
        self.zone_ttl = zone_info["ttl"]

    def _create_record(self, rtype, name, content):
        """Create record. If it already exists, do nothing."""
        if not self._list_records(rtype, name, content):
            self._update_records(
                [{}],
                {
                    "type": rtype,
                    "hostname": self._relative_name(name),
                    "destination": content,
                    "priority": self._get_lexicon_option("priority"),
                },
            )
        LOGGER.debug("create_record: %s", True)
        return True

    def _list_records(self, rtype=None, name=None, content=None):
        """List all records. Return an empty list if no records found.
        ``rtype``, ``name`` and ``content`` are used to filter records."""
        records = [
            {
                "id": record["id"],
                "type": record["type"],
                "name": self._full_name(record["hostname"]),
                "content": record["destination"],
                "priority": record["priority"],
                "ttl": self.zone_ttl,
            }
            for record in self._raw_records(None, rtype, name, content)
        ]
        LOGGER.debug("list_records: %s", records)
        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        """Create or update a record."""
        records = self._raw_records(identifier, rtype, name, content)
        self._update_records(
            records,
            {
                "type": rtype,
                "hostname": self._relative_name(name),
                "destination": content,
                "priority": self._get_lexicon_option("priority"),
            },
        )
        LOGGER.debug("update_record: %s", True)
        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """Delete an existing record. If record does not exist, do nothing."""
        records = self._raw_records(identifier, rtype, name, content)
        LOGGER.debug("delete_records: %s", [rec["id"] for rec in records])
        self._update_records(
            records,
            {
                "deleterecord": True,
                "type": rtype,
                "hostname": name,
                "destination": content,
            },
        )
        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers

    def _raw_records(self, identifier=None, rtype=None, name=None, content=None):
        """Return list of record dicts in the netcup API convention."""
        record_fields = {
            "id": identifier,
            "type": rtype,
            "hostname": name and self._relative_name(name),
            "destination": content,
        }
        # type/hostname/destination of the dnsrecord type are mandatory (even
        # when deleting), and must be queried if not all were specified:
        if all(record_fields.values()):
            return [record_fields]
        data = self._apicall("infoDnsRecords", domainname=self.domain)
        records = data.get("dnsrecords", [])
        return [
            record
            for record in records
            if all(record[k] == v for k, v in record_fields.items() if v)
        ]

    def _update_records(self, records, data):
        """Insert or update a list of DNS records, specified in the netcup API
        convention.

        The fields ``hostname``, ``type``, and ``destination`` are mandatory
        and must be provided either in the record dict or through ``data``!
        """
        data = {k: v for k, v in data.items() if v}
        records = [dict(record, **data) for record in records]
        return self._apicall(
            "updateDnsRecords",
            domainname=self.domain,
            dnsrecordset={"dnsrecords": records},
        ).get("dnsrecords", [])

    def _apicall(self, method, **params):
        """Call an API method and return response data. For more info, see:
        https://ccp.netcup.net/run/webservice/servers/endpoint"""
        LOGGER.debug("%s(%r)", method, params)
        auth = {
            "customernumber": self._get_provider_option("auth_customer_id"),
            "apikey": self._get_provider_option("auth_api_key"),
        }
        if method == "login":
            auth["apipassword"] = self._get_provider_option("auth_api_password")
        else:
            auth["apisessionid"] = self.api_session_id
        if not all(auth.values()):
            raise Exception("No valid authentication mechanism found")
        data = self._request(
            "POST", url="", data={"action": method, "param": dict(params, **auth)}
        )
        if data["status"] != "success":
            raise Exception(f"{data['longmessage']} ({data['statuscode']})")
        return data.get("responsedata", {})

    def _request(self, action="GET", url="/", data=None, query_params=None):
        """Perform network request to configured JSON endpoint."""
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        response = requests.request(
            action,
            self.api_endpoint + url,
            data=json.dumps(data),
            params=query_params,
            headers=default_headers,
        )
        response.raise_for_status()
        return response.json()
