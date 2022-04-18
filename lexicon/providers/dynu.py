"""Module provider for Dynu.com"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["dynu.com"]
FREE_SERVICE_LIMIT = 4
MEMBERSHIP_DETAILS = "https://www.dynu.com/en-US/Membership"


def provider_parser(subparser):
    """Module provider for Dynu.com"""
    subparser.add_argument("--auth-token", help="specify api key for authentication")


class Provider(BaseProvider):
    """Provider class for Dynu.com"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.dynu.com/v2"

    def _authenticate(self):
        data = self._get("/dns")
        domains = data["domains"]
        for domain in domains:
            if domain["name"].lower() == self.domain.lower():
                self.domain_id = domain["id"]
                break
        else:
            raise AuthenticationError("No matching domain found")

    # Create record. If record already exists with the same content, do nothing.
    def _create_record(self, rtype, name, content):
        record = self._to_dynu_record(rtype, name, content)

        if self._get_lexicon_option("ttl"):
            record["ttl"] = self._get_lexicon_option("ttl")

        created = False
        try:
            payload = self._post(f"/dns/{self.domain_id}/record", record)
            created = self._from_dynu_record(payload)
        except requests.exceptions.HTTPError as error:
            # HTTP 501 is expected when a record with the same type and content is sent to the
            # server.
            if error.response.status_code == 501:
                created = True
            else:
                raise error
        LOGGER.debug("create_record: %s", created)
        return created

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        payload = self._get(f"/dns/{self.domain_id}/record")

        records = []
        for record in payload["dnsRecords"]:
            processed_record = self._from_dynu_record(record)
            records.append(processed_record)

        len_all = len(records)

        if rtype:
            records = [record for record in records if record["type"] == rtype]

        if name:
            records = [
                record for record in records if record["name"] == self._full_name(name)
            ]

        if content:
            records = [record for record in records if record["content"] == content]

        len_removed = len_all - len(records)
        if len_removed:
            LOGGER.debug("list_records: removed %d, total %d", len_removed, len_all)

        LOGGER.debug("list_records: %s", records)
        return records

    # Update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        records = {}
        if identifier is None:
            records = self._list_records(rtype, name, None)
            records = {rec["id"]: rec for rec in records}
        else:
            if name is not None:
                # check if new name matches old one
                # dynu prohibits changing the node name, so we have to delete
                # and create a new record then
                original = self._fetch_record(identifier)
                orig_name = self._relative_name(original["name"]).lower()
                new_name = self._relative_name(name).lower()
                if orig_name != new_name:
                    LOGGER.info(
                        "Cannot change node name from %s to %s, deleting %s and creating new",
                        orig_name,
                        new_name,
                        identifier,
                    )
                    self._delete_record(identifier)
                    return self._create_record(rtype, name, content)

            records = {identifier: self._to_dynu_record(rtype, None, content)}

        for ident, rec in records.items():
            add_rec = self._to_dynu_record(
                rec["type"], self._relative_name(rec["name"]), rec["content"]
            )
            payload = self._post(f"/dns/{self.domain_id}/record/{ident}", add_rec)
            update = self._from_dynu_record(payload)
            LOGGER.debug("update_record: %s", update)
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
            try:
                self._delete(f"/dns/{self.domain_id}/record/{record_id}")
                LOGGER.debug("delete_record: %s", record_id)
            except requests.exceptions.HTTPError as error:
                if error.response.status_code == 501:
                    LOGGER.info("delete_record: %s does not exist", record_id)
                    continue
                raise error

        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data:
            data = json.dumps(data)

        LOGGER.debug("Request: %s %s with data %s", action, url, data)

        response = requests.request(
            action,
            self.api_endpoint + url,
            data=data,
            headers={
                "API-Key": self._get_provider_option("auth_token"),
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        LOGGER.debug("Response: %s", response)
        # if the request fails for any reason, throw an error.
        if response.status_code == 503:
            raise RuntimeError(
                "Too many entries, limit for free service is {0}, see {1}".format(
                    FREE_SERVICE_LIMIT, MEMBERSHIP_DETAILS
                )
            )
        response.raise_for_status()
        return response.json()

    # Fetch a record by its ID
    def _fetch_record(self, identifier):
        payload = self._get(f"/dns/{self.domain_id}/record/{identifier}")
        return self._from_dynu_record(payload)

    # Takes a Dynu.com record and puts it into lexicon-shape
    @staticmethod
    def _from_dynu_record(record):
        rtype = record["recordType"]
        options = {"enabled": "state", "lastUpdate": "updatedOn"}
        options = {k: record[v] for k, v in options.items() if v in record}
        options["raw"] = record

        # map additional fields depending on the record type
        # the result takes the record type as key, and all options of the
        # matching key in the following dict as dict of values,
        # e.g.
        # 'options': {
        #     'CNAME': {
        #         'host': 'example.com'
        #     }
        # }
        mapping = {
            "A": {"ipv4": "ipv4Address", "group": "group"},
            "AAAA": {"ipv6": "ipv6Address", "group": "group"},
            "CNAME": {"host": "host"},
            "LOC": {
                "lat": "latitude",
                "long": "longitude",
                "alt": "altitude",
                "size": "size",
                "hPrec": "horizontalPrecision",
                "vPrec": "verticalPrecision",
            },
            "MX": {"host": "host", "priority": "priority"},
            "NS": {"host": "host"},
            "PTR": {"host": "host"},
            "SRV": {"host": "host", "priority": "priority", "weight": "weight"},
            "TXT": {"data": "textData"},
        }.get(rtype, {})
        options[rtype] = {k: record[v] for k, v in mapping.items() if v in record}

        out_record = {
            "id": record["id"],
            "type": rtype,
            "name": record["hostname"],
            "ttl": record["ttl"],
            "options": options,
        }

        # format the content as noted in the spec, e.g. take everything
        # in the raw DNS response after the record type, and remove quotations
        # Example:
        #   example.com. 120 IN TXT \"txt-value=thisIsATest\"
        # Becomes:
        #   txt-value=thisIsATest
        if record["content"]:
            content = record["content"]
            content = content.split(rtype)[1]
            content = content.strip()
            content = content.replace('"', "")
            out_record["content"] = content

        return out_record

    # Takes record input and puts it into a format the Dynu.com API supports
    def _to_dynu_record(self, rtype, name, content):
        if rtype == "LOC":
            raise NotImplementedError("LOC is not available for this provider")

        if rtype == "SPF":
            raise NotImplementedError("SPF entries are not supported")

        output = {"recordType": rtype, "state": True}
        if name is not None:
            output["nodeName"] = self._relative_name(name)

        cnt_split = content.split(" ")
        output.update(
            {
                "A": (lambda: {"ipv4Address": content}),
                "AAAA": (lambda: {"ipv6Address": content}),
                "CNAME": (lambda: {"host": content}),
                "MX": (lambda: {"priority": cnt_split[0], "host": cnt_split[1]}),
                "NS": (lambda: {"host": content}),
                "PTR": (lambda: {"host": content}),
                "SRV": (
                    lambda: {
                        "priority": cnt_split[0],
                        "weight": cnt_split[1],
                        "port": cnt_split[2],
                        "host": cnt_split[3],
                    }
                ),
                "TXT": (lambda: {"textData": content}),
            }.get(rtype, lambda: {})()
        )
        return output
