import datetime
import hashlib
import json
from typing import Optional, Dict, List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

NAMESERVER_DOMAINS = [
    "wedos.net",
    "wedos.eu",
    "wedos.cz",
    "wedos.com"]


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.description = """
    """
    subparser.add_argument(
        "--auth-username",
        help="specify email address for authentication",
    )
    subparser.add_argument(
        "--auth-pass",
        help="specify password for WAPI",
    )


def filter_rtype(rtype, rec):
    if rec["type"] == rtype:
        return True
    return False


def filter_name(name, rec):
    if rec["name"] == name:
        return True
    return False


class Provider(BaseProvider):
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.wedos.com/wapi/json"

    @staticmethod
    def _auth_hash(login, password):
        passhash = hashlib.sha1(password.encode('utf8')).hexdigest()
        phrase = login + passhash + datetime.datetime.now().strftime('%H')
        return hashlib.sha1(phrase.encode('utf8')).hexdigest()

    def _authenticate(self):

        payload = self._post(data=self._create_payload('dns-domains-list', ''))
        domains = payload["response"]["data"]["domain"]
        for record in domains:
            if record["name"] == self.domain:
                self.domain_id = record["name"]
                break
            else:
                raise AuthenticationError("No domain found")

        self.domain_id = self.domain

    def _create_payload(self, command, payload_data):
        data = {'request': {'user': self._get_provider_option("auth_username"),
                            'auth': self._auth_hash(self._get_provider_option("auth_username"),
                                                    self._get_provider_option("auth_pass")),
                            'command': command,
                            'data': payload_data
                            }}
        return {'request': json.dumps(data)}

    def _create_record(self, rtype: str, name: str, content: str) -> bool:
        data = {
            'type': rtype,
            'name': self._full_name(name),
            'rdata': content,
            'domain': self.domain_id
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        payload = self._post(data=self._create_payload('dns-row-add', data))
        code = payload["response"]["code"]
        if code == 1000:
            validation = self._validate_changes()
            if validation:
                return True
            else:
                return False
        else:
            return False

    def _list_records(self, rtype: Optional[str] = None, name: Optional[str] = None, content: Optional[str] = None) -> \
            List[Dict]:
        payload = self._post(data=self._create_payload('dns-rows-list', {'domain': self.domain_id}))
        records = []
        dns_records = payload["response"]["data"]["row"]
        for record in dns_records:
            processed_record = {
                "type": record["rdtype"],
                "name": record["name"],
                "ttl": record["ttl"],
                "content": record["rdata"],
                "id": record["ID"],
            }
            records.append(processed_record)
        if rtype is not None:
            records = list(filter(lambda rec: filter_rtype(rtype, rec), records))
        if name is not None:
            records = list(filter(lambda rec: filter_name(name, rec), records))

        return records

    def _update_record(self, identifier: Optional[str] = None, rtype: Optional[str] = None, name: Optional[str] = None,
                       content: Optional[str] = None) -> bool:
        if identifier is None:
            records = self._list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            elif len(records) < 1:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )

        data = {
            'type': rtype,
            'name': self._full_name(name),
            'rdata': content,
            'domain': self.domain_id,
            'row_id': identifier
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        payload = self._post(data=self._create_payload('dns-row-update', data))
        code = payload["response"]["code"]
        if code == 1000:
            validation = self._validate_changes()
            if validation:
                return True
            else:
                return False
        else:
            return False

    def _delete_record(self, identifier: Optional[str] = None, rtype: Optional[str] = None, name: Optional[str] = None,
                       content: Optional[str] = None) -> bool:
        if identifier is None:
            records = self._list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            elif len(records) < 1:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )

        data = {
            'domain': self.domain_id,
            'row_id': identifier
        }
        if self._get_lexicon_option("ttl"):
            data["ttl"] = self._get_lexicon_option("ttl")

        payload = self._post(data=self._create_payload('dns-row-delete', data))
        code = payload["response"]["code"]
        if code == 1000:
            validation = self._validate_changes()
            if validation:
                return True
            else:
                return False
        else:
            return False

    def _validate_changes(self) -> bool:
        data = {
            'name': self.domain_id
        }

        payload = self._post(data=self._create_payload('dns-domain-commit', data))
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
