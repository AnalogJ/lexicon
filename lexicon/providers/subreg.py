"""Provide support to Lexicon for Subreg.cz DNS changes."""

from __future__ import absolute_import
from __future__ import print_function

import logging

import collections

from .base import Provider as BaseProvider

try:
    import pysimplesoap # Optional dependency
except:
    pass

logger = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify user name used to authenticate")
    subparser.add_argument("--auth-password", help="specify password used to authenticate")

class Provider(BaseProvider):
    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.ssid = None

        self.api = pysimplesoap.client.SoapClient(
            location="https://subreg.cz/soap/cmd.php?soap_format=1",
            namespace="http://subreg.cz/types")

    def authenticate(self):
        if not self.options['auth_username'] or not self.options['auth_password']:
            raise Exception('No valid authentication data passed, expected: auth-username and auth-password')
        response = self._request("Login",
                                 self.LOGIN_RESPONSE_TYPES,
                                 login=self.options['auth_username'],
                                 password=self.options['auth_password'])
        if 'ssid' in response:
            self.ssid = response['ssid']
            domains = self.domains_list()
            if any(domain['name'] == self.options['domain'] for domain in domains):
                self.domain_id = self.options['domain']
            else:
                raise Exception("Unknown domain")
        else:
            raise Exception("No SSID provided by server")

    # Create record. If record already exists with the same content, do nothing.
    def create_record(self, type, name, content):
        found = self.list_records(type, name, content)
        if len(found) > 0:
            return True

        record = self._create_record(None, type, name, content,
                                     self.options.get('ttl'),
                                     self.options.get('priority'))
        self._request("Add_DNS_Record",
                      self.ADD_DNS_RECORD_RESPONSE_TYPES,
                      domain=self.options['domain'],
                      record=record)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        response = self._request("Get_DNS_Zone",
                                 self.GET_DNS_ZONE_RESPONSE_TYPES,
                                 domain=self.options['domain'])
        records = list()
        if 'records' in response:
            relative_name = self._relative_name(name) if name else None
            # Interpret empty string as None because pysimplesoap does so too
            if relative_name == "":
                relative_name = None

            filtered_records = [record for record in response['records'] if
                        (type is None or record['type'] == type) and
                        (name is None or record['name'] == relative_name) and
                        (content is None or ('content' in record and record['content'] == content))]
            for filtered_record in filtered_records:
                filtered_name = filtered_record['name'] if filtered_record['name'] else ""
                record = dict()
                record['id'] = filtered_record['id']
                record['type'] = filtered_record['type']
                record['name'] = self._full_name(filtered_name) if filtered_name else self.options['domain']
                if 'content' in filtered_record:
                    record['content'] = filtered_record['content']
                if 'ttl' in filtered_record:
                    record['ttl'] = filtered_record['ttl']
                if 'priority' in filtered_record:
                    record['priority'] = filtered_record['priority']
                records.append(record)
        return records

    # Update a record. Identifier must be specified.
    # We are unable to update name in this way - not supported by Subreg
    def update_record(self, identifier, type=None, name=None, content=None):
        if identifier is not None:
            update_id = identifier
        else:
            record = self._guess_record(type, name)
            update_id = record['id']

        record = self._create_record(update_id, type, None, content,
                                     self.options.get('ttl'),
                                     self.options.get('priority'))
        self._request("Modify_DNS_Record",
                      self.MODIFY_DNS_RECORD_RESPONSE_TYPES,
                      domain=self.options['domain'],
                      record=record)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        to_delete_ids = list()
        if identifier:
            to_delete_ids.append(identifier)
        else:
            for record in self.list_records(type, name, content):
                to_delete_ids.append(record["id"])

        for to_delete_id in to_delete_ids:
            record = { 'id': to_delete_id }
            self._request("Delete_DNS_Record",
                          self.DELETE_DNS_RECORD_RESPONSE_TYPES,
                          domain=self.options['domain'],
                          record=record)
        return True

    # Get list of registered domains
    def domains_list(self):
        response = self._request("Domains_List",
                                 self.DOMAINS_LIST_RESPONSE_TYPES)
        return response['domains'] if 'domains' in response else list()

    def _create_record(self, identifier, type, name, content, ttl, priority):
        record = collections.OrderedDict()
        if identifier:
            record['id'] = identifier
        record['type'] = type
        if name:
            record['name'] = self._relative_name(name)
        if content:
            record['content'] = content
        if ttl:
            record['ttl'] = ttl
        if priority:
            record['priority'] = priority
        return record

    def _guess_record(self, type, name=None, content=None):
        records = self.list_records(type=type, name=name, content=content)
        if len(records) == 1:
            return records[0]
        elif len(records) > 1:
            raise Exception('Identifier was not provided and several existing records match the request for {0}/{1}'.format(type,name))
        else:
            raise Exception('Identifier was not provided and no existing records match the request for {0}/{1}'.format(type,name))

    def _request(self, command, response_types, **kwargs):
        """Make request parse response"""
        args = dict(kwargs)
        if self.ssid:
            args['ssid'] = self.ssid
        method = getattr(self.api, command)
        raw_response = method(**args)
        response = self._parse_response(raw_response, response_types)
        self.response = response
        self.raw_response = raw_response
        if response and 'status' in response:
            if response['status'] == 'error':
                raise SubregError(
                    message=response['error']['errormsg'],
                    major=response['error']['errorcode']['major'],
                    minor=response['error']['errorcode']['minor']
                )
            if response['status'] == 'ok':
                return response['data'] if 'data' in response else dict()
            else:
                raise Exception("Invalid status found in SOAP response")
        raise Exception('Invalid response')

    def _parse_response(self, response, response_types):
        """Recursively parse response"""
        if hasattr(response, 'response'):
            expected_response_types = {
                "response": response_types
                }
            parsed = response.response.unmarshall(expected_response_types)
            return parsed['response']
        else:
            raise Exception("No reponse tag found in SOAP response")

    ERROR_INFO_TYPES = {
        "errormsg": str,
        "errorcode": {
            "major": int,
            "minor": int
            }
        }
    LOGIN_RESPONSE_TYPES = {
        "status": str,
        "data": {
            "ssid": str
            },
        "error": ERROR_INFO_TYPES,
        }

    GET_DNS_ZONE_RESPONSE_TYPES = {
        "status": str,
        "data": {
            "domain": str,
            "records": [{
                "id": int,
                "name": str,
                "type": str,
                "content": str,
                "prio": int,
                "ttl": int
                }]
            },
        "error": ERROR_INFO_TYPES,
        }

    ADD_DNS_RECORD_RESPONSE_TYPES = {
        "status": str,
        "data": {},
        "error": ERROR_INFO_TYPES,
        }

    MODIFY_DNS_RECORD_RESPONSE_TYPES = {
        "status": str,
        "data": {},
        "error": ERROR_INFO_TYPES,
        }

    DELETE_DNS_RECORD_RESPONSE_TYPES = {
        "status": str,
        "data": {},
        "error": ERROR_INFO_TYPES,
        }

    DOMAINS_LIST_RESPONSE_TYPES = {
        "status": str,
        "data": {
            "count": int,
            "domains": [{
                "name": str,
                "expire": str,
                "autorenew": int
                }]
            },
        "error": ERROR_INFO_TYPES,
        }

class SubregError(Exception):
    def __init__(self, major, minor, message):
        self.major = int(major)
        self.minor = int(minor)
        self.message = message

    def __str__(self):
        return 'Major: {} Minor: {} Message: {}'.format(self.major, self.minor, self.message)
