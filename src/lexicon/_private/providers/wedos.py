import datetime
import hashlib
import json
from argparse import ArgumentParser
from typing import Dict, List, Optional

import requests

from lexicon.exceptions import AuthenticationError, LexiconError
from lexicon.interfaces import Provider as BaseProvider


def _filter_rtype(rtype: str, rec) -> bool:
    if rec["type"] == rtype:
        return True
    return False


def _filter_name(name: str, rec) -> bool:
    if rec["name"] == name:
        return True
    return False


def _filter_content(content: str, rec) -> bool:
    if rec["content"] == content:
        return True
    return False


class Provider(BaseProvider):
    @staticmethod
    def get_nameservers() -> List[str]:
        return ["wedos.net", "wedos.eu", "wedos.cz", "wedos.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument(
            "--auth-username",
            help="specify email address for authentication",
        )
        parser.add_argument(
            "--auth-pass",
            help="specify password for WAPI",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.wedos.com/wapi/json"

    @staticmethod
    def _auth_hash(login, password):
        passhash = hashlib.sha1(password.encode("utf8")).hexdigest()
        phrase = login + passhash + datetime.datetime.now().strftime("%H")
        return hashlib.sha1(phrase.encode("utf8")).hexdigest()

    def authenticate(self):
        payload = self._post(data=self._create_payload("dns-domains-list", ""))
        domains = payload["response"]["data"]["domain"]
        for record in domains:
            if record["name"] == self.domain:
                self.domain_id = record["name"]
                break
            else:
                raise AuthenticationError("No domain found")

        self.domain_id = self.domain

    def cleanup(self) -> None:
        pass

    def _create_payload(self, command, payload_data):
        data = {
            "request": {
                "user": self._get_provider_option("auth_username"),
                "auth": self._auth_hash(
                    self._get_provider_option("auth_username"),
                    self._get_provider_option("auth_pass"),
                ),
                "command": command,
                "data": payload_data,
            }
        }
        return {"request": json.dumps(data)}

    def create_record(self, rtype: str, name: str, content: str) -> bool:
        records = self.list_records(rtype, name, content)
        if len(records) == 1:
            return True
        data = {
            "type": rtype,
            "name": self._full_name(name),
            "rdata": content,
            "domain": self.domain_id,
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        payload = self._post(data=self._create_payload("dns-row-add", data))
        code = payload["response"]["code"]
        if code == 1000:
            validation = self._commit_changes()
            if validation:
                return True
            else:
                raise LexiconError("Cannot commit changes")
        else:
            raise LexiconError("Cannot create records")

    def list_records(
        self,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> List[Dict]:
        data = self._create_payload("dns-rows-list", {"domain": self.domain_id})
        payload = self._post(data=data)
        records = []
        dns_records = payload["response"]["data"]["row"]
        for record in dns_records:
            processed_record = {
                "type": record["rdtype"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["rdata"],
                "id": record["ID"],
            }
            records.append(processed_record)
        if rtype is not None:
            records = list(rec for rec in records if _filter_rtype(rtype, rec))
        if name is not None:
            records = list(
                rec for rec in records if _filter_name(self._full_name(name), rec)
            )
        if content is not None:
            records = list(rec for rec in records if _filter_content(content, rec))

        return records

    def update_record(
        self,
        identifier: Optional[str] = None,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        if not identifier:
            records = self.list_records(rtype, name, content)
            identifiers = [record["id"] for record in records]
        else:
            identifiers = [identifier]

        if len(identifiers) == 0:
            return True
        payloads = []
        for record_id in identifiers:
            data = {
                "type": rtype,
                "rdata": content,
                "domain": self.domain_id,
                "row_id": record_id,
            }
            if name:
                data["name"] = self._full_name(name)
            if self._get_lexicon_option("ttl"):
                data["ttl"] = self._get_lexicon_option("ttl")
            payloads.append(
                self._post(data=self._create_payload("dns-row-update", data))
            )

        if all(payload["response"]["code"] == 1000 for payload in payloads):
            validation = self._commit_changes()
            if validation:
                return True
            else:
                raise LexiconError("Cannot commit changes")
        else:
            raise LexiconError("Cannot update records")

    def delete_record(
        self,
        identifier: Optional[str] = None,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        if not identifier:
            records = self.list_records(rtype, name, content)
            identifiers = [record["id"] for record in records]
        else:
            identifiers = [identifier]

        if len(identifiers) == 0:
            return True
        payloads = []
        for record_id in identifiers:
            data = {"domain": self.domain_id, "row_id": record_id}
            payloads.append(
                self._post(data=self._create_payload("dns-row-delete", data))
            )

        if all(payload["response"]["code"] == 1000 for payload in payloads):
            validation = self._commit_changes()
            if validation:
                return True
            else:
                raise LexiconError("Cannot commit changes")
        else:
            raise LexiconError("Cannot delete records")

    def _commit_changes(self) -> bool:
        data = {"name": self.domain_id}

        payload = self._post(data=self._create_payload("dns-domain-commit", data))
        code = payload["response"]["code"]
        if code == 1000:
            return True
        else:
            return False

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}

        response = requests.request(
            action,
            self.api_endpoint,
            data=data,
        )

        response.raise_for_status()
        return response.json()
