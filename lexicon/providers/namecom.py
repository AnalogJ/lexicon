"""Module provider for Name.com"""
from __future__ import absolute_import

import logging

from requests import HTTPError, Session
from requests.auth import HTTPBasicAuth

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["name.com"]

DUPLICATE_ERROR = {
    "message": "Invalid Argument",
    "details": "Parameter Value Error - Duplicate Record",
}


def provider_parser(subparser):
    """Configure a subparser for Name.com."""

    subparser.add_argument("--auth-username", help="specify a username")
    subparser.add_argument("--auth-token", help="specify an API token")


class NamecomLoader(
    object
):  # pylint: disable=useless-object-inheritance,too-few-public-methods
    """Loader that handles pagination for the Name.com provider."""

    def __init__(self, get, url, data_key, next_page=1):
        self.get = get
        self.url = url
        self.data_key = data_key
        self.next_page = next_page

    def __iter__(self):
        while self.next_page:
            response = self.get(self.url, {"page": self.next_page})
            for data in response[self.data_key]:
                yield data
            self.next_page = response.get("next_page")


class NamecomProvider(BaseProvider):
    """Provider implementation for Name.com."""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = "https://api.name.com/v4"
        self.session = Session()

    def _authenticate(self):
        self.session.auth = HTTPBasicAuth(
            username=self._get_provider_option("auth_username"),
            password=self._get_provider_option("auth_token"),
        )

        # checking domain existence
        domain_name = self.domain
        for domain in NamecomLoader(self._get, "/domains", "domains"):
            if domain["domainName"] == domain_name:
                self.domain_id = domain_name
                return

        raise Exception("{} domain does not exist".format(domain_name))

    def _create_record(self, rtype, name, content):
        data = {
            "type": rtype,
            "host": self._relative_name(name),
            "answer": content,
            "ttl": self._get_lexicon_option("ttl"),
        }

        if rtype in ("MX", "SRV"):
            # despite the documentation says a priority is
            # required for MX and SRV, it's actually optional
            priority = self._get_lexicon_option("priority")
            if priority:
                data["priority"] = priority

        url = "/domains/{}/records".format(self.domain)
        try:
            record_id = self._post(url, data)["id"]
        except HTTPError as error:
            response = error.response
            if response.status_code == 400 and response.json() == DUPLICATE_ERROR:
                LOGGER.warning("create_record: duplicate record has been skipped")
                return True
            raise

        LOGGER.debug("create_record: record %s has been created", record_id)

        return record_id

    def _list_records(self, rtype=None, name=None, content=None):
        url = "/domains/{}/records".format(self.domain)
        records = []

        for raw in NamecomLoader(self._get, url, "records"):
            record = {
                "id": raw["id"],
                "type": raw["type"],
                "name": raw["fqdn"][:-1],
                "ttl": raw["ttl"],
                "content": raw["answer"],
            }
            records.append(record)

        LOGGER.debug("list_records: retrieved %s records", len(records))

        if rtype:
            records = [record for record in records if record["type"] == rtype]
        if name:
            name = self._full_name(name)
            records = [record for record in records if record["name"] == name]
        if content:
            records = [record for record in records if record["content"] == content]

        LOGGER.debug("list_records: filtered %s records", len(records))

        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if not identifier:
            if not (rtype and name):
                raise ValueError("Record identifier or rtype+name must be specified")
            records = self._list_records(rtype, name)
            if not records:
                raise Exception("There is no record to update")

            if len(records) > 1:
                filtered_records = [
                    record for record in records if record["content"] == content
                ]
                if filtered_records:
                    records = filtered_records

                if len(records) > 1:
                    raise Exception(
                        "There are multiple records to update: {}".format(
                            ", ".join(record["id"] for record in records)
                        )
                    )

            record_id = records[0]["id"]
        else:
            record_id = identifier

        data = {"ttl": self._get_lexicon_option("ttl")}

        # even though the documentation says a type and an answer
        # are required, they are not required actually
        if rtype:
            data["type"] = rtype
        if name:
            data["host"] = self._relative_name(name)
        if content:
            data["answer"] = content

        url = "/domains/{}/records/{}".format(self.domain, record_id)
        record_id = self._put(url, data)["id"]
        logging.debug("update_record: record %s has been updated", record_id)

        return record_id

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier:
            if not (rtype and name):
                raise ValueError("Record identifier or rtype+name must be specified")
            records = self._list_records(rtype, name, content)
            if not records:
                LOGGER.warning("delete_record: there is no record to delete")
                return False
            record_ids = [record["id"] for record in records]
        else:
            record_ids = [
                identifier,
            ]

        for record_id in record_ids:
            url = "/domains/{}/records/{}".format(self.domain, record_id)
            self._delete(url)
            LOGGER.debug("delete_record: record %s has been deleted", record_id)

        return True

    def _get_raw_record(self, record_id):
        url = "/domains/{}/records/{}".format(self.domain, record_id)
        return self._get(url)

    def _request(self, action="GET", url="/", data=None, query_params=None):
        response = self.session.request(
            method=action, url=self.api_endpoint + url, json=data, params=query_params
        )
        response.raise_for_status()
        return response.json()


Provider = NamecomProvider
