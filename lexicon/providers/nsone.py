"""Module provider for NSOne"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["nsone.net"]


def provider_parser(subparser):
    """Configure provider parser for NSOne"""
    subparser.add_argument("--auth-token", help="specify token for authentication")


class Provider(BaseProvider):
    """Provider class for NSOne"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.nsone.net/v1"

    def _authenticate(self):

        payload = self._get(f"/zones/{self.domain}")

        if not payload["id"]:
            raise AuthenticationError("No domain found")

        self.domain_id = self.domain

    def _get_record_set(self, name, rtype):
        try:
            payload = self._get(f"/zones/{self.domain_id}/{name}/{rtype}")
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                return None
            raise

        return {
            "type": payload["type"],
            "name": payload["domain"],
            "ttl": payload["ttl"],
            "answers": payload["answers"],
        }

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        name = self._full_name(name)
        existing_record_set = self._get_record_set(name, rtype)
        if existing_record_set:

            def _record_set_has_answer(record_set, content):
                for answer in record_set["answers"]:
                    if content in answer["answer"]:
                        return True
                return False

            if not _record_set_has_answer(existing_record_set, content):
                existing_record_set["answers"].append({"answer": [content]})
                self._post(
                    f"/zones/{self.domain_id}/{name}/{rtype}", existing_record_set
                )
        else:
            record = {
                "type": rtype,
                "domain": name,
                "ttl": self._get_lexicon_option("ttl"),
                "zone": self.domain_id,
                "answers": [{"answer": [content]}],
            }
            payload = {}
            try:
                payload = self._put(f"/zones/{self.domain_id}/{name}/{rtype}", record)
            except requests.exceptions.HTTPError as error:
                # http 400 is ok here, because the record probably already exists
                if error.response.status_code != 400:
                    raise

            LOGGER.debug("create_record: %s", "id" in payload)

        return True

    def _find_record(self, domain, _type=None):
        """search for a record on NS1 across zones. returns None if not found."""

        def _is_matching(record):
            """filter function for records"""

            if domain and record.get("domain", None) != domain:
                return False
            if _type and record.get("type", None) != _type:
                return False
            return True

        payload = self._get(f"/search?q={domain}&type=record")
        for record in payload:
            if _is_matching(record):
                match = record
                break
        else:
            # no such domain on ns1
            return None

        record = self._get(f"/zones/{match['zone']}/{match['domain']}/{match['type']}")
        if record.get("message", None):
            return None  # {"message":"record not found"}
        short_answers = [x["answer"][0] for x in record["answers"]]

        # ensure a compatibility level with self._list_records
        record["short_answers"] = short_answers
        return record

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        def _resolve_link(record, recurse=0):
            # https://ns1.com/articles/cname-alias-and-linked-records
            # - recursion is allowed
            # - link source and link target are always of the same rtype
            # - target can be anywhere on ns1, not necessarily self.domain_id.
            if record.get("link", None) is None:
                # not a linked record
                return record

            if recurse < 1:
                return None

            match = self._find_record(record["link"], _type=record["type"])
            if not match:
                return None

            return _resolve_link(match, recurse=recurse - 1)

        payload = self._get(f"/zones/{self.domain_id}")
        records = []
        for record in payload["records"]:

            if rtype and record["type"] != rtype:
                continue

            if name and record["domain"] != self._full_name(name):
                continue

            link_target = _resolve_link(record, recurse=3)

            if link_target and link_target.get("short_answers", None):
                # target found (could be the same as orig record)
                answers = link_target["short_answers"]
            else:
                # recursion limit reached. or unhandled record format.
                answers = []

            if content and content not in answers:
                continue

            for answer in answers:
                processed_record = {
                    "type": record["type"],
                    "name": record["domain"],
                    "ttl": record["ttl"],
                    "content": answer,
                    # this id is useless unless your doing record linking. Lets return the
                    # original record identifier.
                    "id": f"{self.domain_id}/{record['domain']}/{record['type']}",
                }
                records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        data = {}
        new_identifier = f"{self.domain_id}/{self._full_name(name)}/{rtype}"

        if new_identifier == identifier or (rtype is None and name is None):
            # the identifier hasnt changed, or type and name are both unspecified,
            # only update the content.
            data["answers"] = [{"answer": [content]}]
            self._post(f"/zones/{identifier}", data)

        else:
            # identifiers are different
            # get the old record, create a new one with updated data, delete the old record.
            old_record = self._get(f"/zones/{identifier}")
            self.create_record(
                rtype or old_record["type"],
                name or old_record["domain"],
                content or old_record["answers"][0]["answer"][0],
            )
            self.delete_record(identifier)

        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if not identifier:
            name = self._full_name(name)

            record_set = self._get_record_set(name, rtype)
            if record_set:
                record_set_new = {
                    "type": record_set["type"],
                    "name": record_set["name"],
                    "ttl": record_set["ttl"],
                    "answers": [],
                }

                if content:
                    for answer in record_set["answers"]:
                        if content not in answer["answer"]:
                            record_set_new["answers"].append(answer)

                if record_set_new["answers"]:
                    self._post(
                        f"/zones/{self.domain_id}/{name}/{rtype}", record_set_new
                    )
                else:
                    self._delete(f"/zones/{self.domain_id}/{name}/{rtype}")
        else:
            self._delete(f"/zones/{identifier}")

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-NSONE-Key": self._get_provider_option("auth_token"),
        }
        default_auth = None

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
            auth=default_auth,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()
