"""Module provider for exoscale"""
from __future__ import absolute_import
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

HOUR = 3600

NAMESERVER_DOMAINS = ['exoscale.ch']


def provider_parser(subparser):
    """Generate subparser for exoscale"""
    subparser.add_argument(
        "--auth-key", help="specify API key for authentication"
    )
    subparser.add_argument(
        "--auth-secret", help="specify API secret for authentication"
    )


class Provider(BaseProvider):
    """Provider class for exoscale"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = 'https://api.exoscale.com/dns'

    def _authenticate(self):
        """An innocent call to check that the credentials are okay."""
        response = self._get("/v1/domains/{0}".format(self.domain))

        self.domain_id = response["domain"]["id"]

    def _create_record(self, rtype, name, content):
        """Create record if doesnt already exist with same content"""
        # check if record already exists
        existing_records = self._list_records(rtype, name, content)
        if len(existing_records) >= 1:
            return True

        record = {
            "record_type": rtype,
            "name": self._relative_name(name),
            "content": content,
        }
        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")
        if self._get_lexicon_option("priority"):
            record["prio"] = self._get_lexicon_option("priority")

        payload = self._post(
            "/v1/domains/{0}/records".format(self.domain),
            {"record": record},
        )

        status = "id" in payload.get("record", {})
        LOGGER.debug("create_record: %s", status)
        return status

    def _list_records(self, rtype=None, name=None, content=None):
        """List all records.

        record_type, name and content are used to filter the records.
        If possible it filters during the query, otherwise afterwards.
        An empty list is returned if no records are found.
        """

        filter_query = {}
        if rtype:
            filter_query["record_type"] = rtype
        if name:
            name = self._relative_name(name)
            filter_query["name"] = name
        payload = self._get(
            "/v1/domains/{0}/records".format(self.domain),
            query_params=filter_query,
        )

        records = []
        for data in payload:
            record = data["record"]

            if content and record["content"] != content:
                continue

            if record["name"] == "":
                rname = self.domain
            else:
                rname = ".".join((record["name"], self.domain))

            processed_record = {
                "type": record["record_type"],
                "name": rname,
                "ttl": record["ttl"],
                "content": record["content"],
                "id": record["id"],
            }
            if record["prio"]:
                processed_record["options"] = {
                    "mx": {"priority": record["prio"]}
                }
            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        """Create or update a record."""
        record = {}

        if not identifier:
            records = self._list_records(rtype, name, content)
            identifiers = [r["id"] for r in records]
        else:
            identifiers = [identifier]

        if name:
            record["name"] = self._relative_name(name)
        if content:
            record["content"] = content
        if self._get_lexicon_option('ttl'):
            record["ttl"] = self._get_lexicon_option('ttl')
        if self._get_lexicon_option('priority'):
            record["prio"] = self._get_lexicon_option('priority')

        LOGGER.debug("update_records: %s", identifiers)

        for record_id in identifiers:
            self._put(
                "/v1/domains/{0}/records/{1}".format(
                    self.domain, identifier
                ),
                record,
            )
            LOGGER.debug("update_record: %s", record_id)

        LOGGER.debug("update_record: %s", True)
        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """Delete an existing record.

        If the record doesn't exist, does nothing.
        """
        if not identifier:
            records = self._list_records(rtype, name, content)
            identifiers = [record["id"] for record in records]
        else:
            identifiers = [identifier]

        LOGGER.debug("delete_records: %s", identifiers)

        for record_id in identifiers:
            self._delete(
                "/v1/domains/{0}/records/{1}".format(
                    self.domain, record_id
                )
            )
            LOGGER.debug("delete_record: %s", record_id)

        LOGGER.debug("delete_record: %s", True)
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        """Performs the request to the API"""
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {"Accept": "application/json"}

        default_headers["X-DNS-Token"] = ":".join(
            (self._get_provider_option("auth_key"),
             self._get_provider_option("auth_secret"))
        )

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            json=data,
            headers=default_headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if response.text and response.json() is None:
            raise Exception("No data returned")

        return response.json() if response.text else None
