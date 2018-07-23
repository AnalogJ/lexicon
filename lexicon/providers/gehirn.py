from __future__ import absolute_import
from __future__ import print_function

import json
import logging
import re
import base64
import copy

import requests
from requests.auth import HTTPBasicAuth

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument(
        "--auth-token", help="specify access token used authenticate to DNS provider")
    subparser.add_argument(
        "--auth-secret", help="specify asscess secret used authenticate to DNS provider")


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
    "A": re.compile("(?P<address>.+)"),
    "AAAA": re.compile("(?P<address>.+)"),
    "CNAME": re.compile("(?P<cname>.+)"),
    "TXT": re.compile("(?P<data>.+)"),
    "NS": re.compile("(?P<nsdname>.+)"),
    "MX": re.compile("(?P<prio>\d+)\s+(?P<exchange>.+)"),
    "SRV": re.compile("(?P<prio>\d+)\s+(?P<weight>\d+)\s+(?P<port>\d+)\s+(?P<target>.+)"),
}


class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.version_id = None
        self.api_endpoint = self.engine_overrides.get(
            'api_endpoint', 'https://api.gis.gehirn.jp/dns/v1')

    def authenticate(self):
        payload = self._get('/zones')

        domains = [item for item in payload if item['name']
                   == self.options['domain']]
        if not domains:
            raise Exception('No domain found')

        self.domain_id = domains[0]["id"]
        self.version_id = domains[0]["current_version_id"]

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        name = self._full_name(name)
        r = self._parse_content(type, content)

        record = None
        records = self._get_records(type=type, name=name)
        if len(records) == 0:
            record = {
                'type': type,
                'name': name,
                'enable_alias': False,
                'ttl': self.options['ttl'],
                'records': [],
            }
        else:
            record = records[0]

        if r in record["records"]:
            logger.debug('create_record: %s', True)
            return True

        record["records"].append(r)
        self._update_record(record)
        logger.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        records = []
        if name:
            name = self._full_name(name)
        for record in self._get_records(type=type, name=name):
            for i, r in enumerate(record["records"]):
                c = self._build_content(record['type'], r)
                processed_record = {
                    'type': record['type'],
                    'name': record['name'].rstrip("."),
                    'ttl': record['ttl'],
                    'content': c,
                    'id': "{}.{}".format(record["id"], base64.b64encode(c.encode("utf-8")).decode("ascii")),
                }
                self._parse_content(
                    record['type'], processed_record["content"])
                records.append(processed_record)

        if content:
            records = [
                record for record in records if record['content'] == content]

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier=None, type=None, name=None, content=None):

        if name:
            name = self._full_name(name)

        record = None
        if not identifier:
            if not (type and name and content):
                raise Exception("type, name and content must be specified.")
                r = self._parse_content(type, content)

            records = self._get_records(type=type, name=name)

            if not records:
                self.create_record(type=type, name=name, content=content)
                logger.debug('update_record: %s', True)
                return True

            record = {
                'id': records[0]["id"],
                'type': type,
                'name': name,
                'enable_alias': False,
                'ttl': self.options['ttl'],
                'records': [self._parse_content(type, content)],
            }

        else:
            # with identifier
            records = self._get_records(identifier=identifier)
            if not records:
                raise Exception('Record identifier could not be found.')

            record = records[0]

            if "." in identifier:
                # modify single record
                self.delete_record(identifier=identifier)
                self.create_record(
                    type=type or record["type"],
                    name=name or record["name"],
                    content=content
                )
                logger.debug('update_record: %s', True)
                return True
            else:
                # update entire record
                if type:
                    record["type"] = type
                if name:
                    record["name"] = name
                record["ttl"] = self.options['ttl']
                if content:
                    record["records"] = [
                        self._parse_content(record["type"], content)]

        self._update_record(record)
        logger.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if identifier:
            if "." not in identifier:
                # delete entire record
                path = '/zones/{}/versions/{}/records/{}'.format(
                    self.domain_id, self.version_id, identifier,
                )
                self._delete(path)
                logger.debug('delete_record: %s', True)
                return True

            record_identifier = identifier.split(".")[1]

            records = self._get_records(identifier=identifier)
            if not records:
                raise Exception('Record identifier could not be found.')

            record = records[0]
            for index, r in enumerate(record["records"]):
                target_content = self._build_content(record['type'], r)
                target_identifier = base64.b64encode(
                    target_content.encode("utf-8")).decode("ascii")

                if target_identifier == record_identifier:
                    del record["records"][index]
                if len(record["records"]) == 0:
                    # delete entire record
                    path = '/zones/{}/versions/{}/records/{}'.format(
                        self.domain_id, self.version_id, record['id'],
                    )
                    self._delete(path)
                else:
                    self._update_record(record)

                logger.debug('delete_record: %s', True)
                return True
            else:
                raise Exception('Record identifier could not be found.')

        r = None
        if name is not None:
            name = self._full_name(name)
        if content is not None:
            content = self._bind_format_target(type, content)
            r = self._parse_content(type, content)

        records = self._get_records(type=type, name=name)

        for record in records:
            if r and r in record["records"]:
                record["records"].remove(r)
                if len(record["records"]):
                    self._update_record(record)
                    continue

            path = '/zones/{}/versions/{}/records/{}'.format(
                self.domain_id, self.version_id, record["id"],
            )
            self._delete(path)

        logger.debug('delete_record: %s', True)
        return True

    # Helpers
    def _full_name(self, name):
        name = super(Provider, self)._full_name(name)
        if not name.endswith("."):
            name += "."
        return name

    def _bind_format_target(self, type, target):
        if type == "CNAME" and not target.endswith("."):
            target += "."
        return target

    def _filter_records(self, records, identifier=None, type=None, name=None):
        filtered_records = []

        if identifier:
            identifier = identifier.split(".")[0]

        for record in records:
            if type and record['type'] != type:
                continue
            if name and record['name'] != name:
                continue
            if identifier and record['id'] != identifier:
                continue
            filtered_records.append(record)
        return filtered_records

    def _get_records(self, identifier=None, type=None, name=None):
        path = '/zones/{}/versions/{}/records'.format(
            self.domain_id, self.version_id)
        return self._filter_records(self._get(path), identifier=identifier, type=type, name=name)

    def _update_record(self, record):
        if record.get("id"):
            # PUT
            path = '/zones/{}/versions/{}/records/{}'.format(
                self.domain_id, self.version_id, record["id"],
            )
            return self._put(path, record)

        # POST
        path = '/zones/{}/versions/{}/records'.format(
            self.domain_id, self.version_id,
        )
        return self._post(path, record)

    def _build_content(self, type, record):
        return BUILD_FORMATS[type].format(**record)

    def _parse_content(self, type, content):
        return FORMAT_RE[type].match(content).groupdict()

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
        default_auth = HTTPBasicAuth(
            self.options['auth_token'], self.options['auth_secret'])

        query_string = ""
        if query_params:
            query_string = json.dumps(query_params)

        r = requests.request(action, self.api_endpoint + url, params=query_string,
                             data=json.dumps(data) if data else None,
                             headers=default_headers,
                             auth=default_auth)
        try:
            # if the request fails for any reason, throw an error.
            r.raise_for_status()
        except:
            logger.error(r.text)
            raise
        return r.json()
