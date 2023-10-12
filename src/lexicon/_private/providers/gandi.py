"""Provide support to Lexicon for Gandi LiveDNS and Gandi XMLRPC changes.

Lexicon provides a common interface for querying and managing DNS services
through those services' APIs. This module implements the Lexicon interface
against the Gandi API.

Gandi introduced the LiveDNS API (http://doc.livedns.gandi.net/) in 2017.
It is the successor of the traditional XMLRPC API, which suffered from
long delays between API-based changes and their activation.
The LiveDNS API has one significant peculiarity: DNS records with the
same name and type are managed as one unit. Thus records cannot be
addressed distinctly, which complicates removal of records significantly.

The Gandi XMLRPC API is different from typical DNS APIs in that Gandi
zone changes are atomic. You cannot edit the currently active
configuration. Any changes require editing either a new or inactive
configuration. Once the changes are committed, then the domain is switched
to using the new zone configuration. This module makes no attempt to
cleanup previous zone configurations.

Note that Gandi domains can share zone configurations. In other words,
I can have domain-a.com and domain-b.com which share the same zone
configuration file. If I make changes to domain-a.com, those changes
will only apply to domain-a.com, as domain-b.com will continue using
the previous version of the zone configuration. This module makes no
attempt to detect and account for that.
"""
import json
import logging
from argparse import ArgumentParser
from builtins import object
from typing import List

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

try:
    import xmlrpclib  # type: ignore
except ImportError:
    import xmlrpc.client as xmlrpclib

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provide Gandi LiveDNS API implementation of Lexicon Provider interface.

    Note that this implementation will delegates its call to GandiRPCSubProvider
    if RPC protocol is used.
    """

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["gandi.net"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument("--auth-token", help="specify Gandi API key")
        parser.add_argument(
            "--api-protocol",
            help="(optional) specify Gandi API protocol to use: rpc (default) or rest",
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.default_ttl = 3600
        self.protocol = self._get_provider_option("api_protocol") or "rpc"

        if self.protocol != "rpc" and self.protocol != "rest":
            raise ValueError(
                "Invalid API protocol specified, should be 'rpc' or 'rest'"
            )

        if self.protocol == "rpc":
            self.rpc_helper = GandiRPCSubProvider(
                self._get_provider_option("auth_token"),
                "https://rpc.gandi.net/xmlrpc/",
                self.domain.lower(),
                self._relative_name,
                self._full_name,
            )
        else:
            self.api_endpoint = "https://api.gandi.net/v5/livedns"

    def authenticate(self):
        if self.protocol == "rpc":
            domain_id = self.rpc_helper.authenticate()
            self.domain_id = domain_id
        else:
            self._get(f"/domains/{self.domain}")
            self.domain_id = self.domain.lower()

    def cleanup(self) -> None:
        pass

    def create_record(self, rtype, name, content):
        if self.protocol == "rpc":
            return self.rpc_helper.create_record(
                rtype,
                self._relative_name(name),
                content,
                self._get_lexicon_option("ttl") or self.default_ttl,
            )

        current_values = [
            record["content"] for record in self.list_records(rtype=rtype, name=name)
        ]
        if current_values != [content]:
            # a change is necessary
            url = (
                f"/domains/{self.domain_id}/records/{self._relative_name(name)}/{rtype}"
            )
            if current_values:
                record = {"rrset_values": current_values + [content]}
                if self._get_lexicon_option("ttl"):
                    record["rrset_ttl"] = (
                        self._get_lexicon_option("ttl")
                        if self._get_lexicon_option("ttl") >= 300
                        else 300
                    )
                self._put(url, record)
            else:
                record = {"rrset_values": [content]}
                # add the ttl, if this is a new record
                if self._get_lexicon_option("ttl"):
                    record["rrset_ttl"] = (
                        self._get_lexicon_option("ttl")
                        if self._get_lexicon_option("ttl") >= 300
                        else 300
                    )
                self._post(url, record)
        LOGGER.debug("create_record: %s", True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        """List all record for the domain in the active Gandi zone."""
        if self.protocol == "rpc":
            return self.rpc_helper.list_records(rtype, name, content)

        try:
            if name is not None:
                if rtype is not None:
                    query_results = [
                        self._get(
                            f"/domains/{self.domain_id}/records/{self._relative_name(name)}/{rtype}"
                        )
                    ]
                else:
                    query_results = self._get(
                        f"/domains/{self.domain_id}/records/{self._relative_name(name)}"
                    )
            else:
                query_results = self._get(f"/domains/{self.domain_id}/records")
                if rtype is not None:
                    query_results = [
                        item for item in query_results if item["rrset_type"] == rtype
                    ]
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                query_results = []
            else:
                raise

        # convert records with multiple values into single-value records
        records = []
        for query_result in query_results:
            for value in query_result["rrset_values"]:
                record = {
                    "type": query_result["rrset_type"],
                    "name": self._full_name(query_result["rrset_name"]),
                    "ttl": query_result["rrset_ttl"],
                    "content": value,
                    "id": query_result["rrset_name"],
                }
                # cleanup potential quoting if suitable
                self._clean_TXT_record(record)
                records.append(record)
        # filter for content, if requested
        if content is not None:
            records = [record for record in records if record["content"] == content]
        LOGGER.debug("list_records: %s", records)
        return records

    # Update a record. Identifier must be specified.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        """Updates the specified record in a new Gandi zone

        'content' should be a string or a list of strings
        """
        if self.protocol == "rpc":
            return self.rpc_helper.update_record(identifier, rtype, name, content)

        data = {}
        if rtype:
            data["rrset_type"] = rtype
        if name:
            data["rrset_name"] = self._relative_name(name)
        if content:
            if isinstance(content, (list, tuple, set)):
                data["rrset_values"] = list(content)
            else:
                data["rrset_values"] = [content]
        if rtype is not None:
            # replace the records of a specific rtype
            effect_id = identifier or self._relative_name(name)
            url = f"/domains/{self.domain_id}/records/{effect_id}/{rtype}"
            self._put(url, data)
        else:
            # replace all records with a matching name
            effect_id = identifier or self._relative_name(name)
            url = f"/domains/{self.domain_id}/records/{effect_id}"
            self._put(url, {"items": [data]})
        LOGGER.debug("update_record: %s", True)
        return True

    # Delete existings records.
    # If records do not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if self.protocol == "rpc":
            return self.rpc_helper.delete_record(identifier, rtype, name, content)

        if not identifier:
            remove_count = 0
            # get all matching (by rtype and name) records - ignore 'content' for now
            records = self.list_records(rtype=rtype, name=name)
            for current_type in set(record["type"] for record in records):
                matching_records = [
                    record for record in records if record["type"] == current_type
                ]
                # collect all non-matching values
                if content is None:
                    remaining_values = []
                else:
                    remaining_values = [
                        record["content"]
                        for record in matching_records
                        if record["content"] != content
                    ]
                url = f"/domains/{self.domain_id}/records/{self._relative_name(name)}/{current_type}"
                if len(matching_records) == len(remaining_values):
                    # no matching item should be removed for this rtype
                    pass
                elif remaining_values:
                    # reduce the list of values
                    self._put(url, {"rrset_values": remaining_values})
                    remove_count += 1
                else:
                    # remove the complete record (possibly with multiple values)
                    self._delete(url)
                    remove_count += 1

            if remove_count == 0:
                raise Exception("Record identifier could not be found.")
        else:
            self._delete(f"/domains/{self.domain_id}/records/{identifier}")

        # is always True at this point, if a non 200 response is returned an error is raised.
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
            "Authorization": "Apikey " + self._get_provider_option("auth_token"),
        }
        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        response = requests.request(
            action,
            url,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if action == "DELETE":
            return ""
        return response.json()


class GandiRPCSubProvider(object):
    """Provide Gandi RPCXML API implementation of Lexicon Provider interface.
    This implementation is called through the main LiveDNS implementation
    is RPC protocol is used.
    """

    def __init__(self, api_key, api_endpoint, domain, relative_name_fn, full_name_fn):
        """Initialize Gandi RCPXML API provider."""
        super(GandiRPCSubProvider, self).__init__()

        self._api_endpoint = api_endpoint
        self._api_key = api_key
        self._domain = domain
        self._relative_name = relative_name_fn
        self._full_name = full_name_fn
        self._api = xmlrpclib.ServerProxy(self._api_endpoint, allow_none=True)
        self._zone_id = None

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider,
    # so it can be used in subsequent calls. Should throw an error if
    # authentication fails for any reason, or if the domain does not exist.
    def authenticate(self):
        """Determine the current domain and zone IDs for the domain."""
        try:
            payload = self._api.domain.info(self._api_key, self._domain)
            self._zone_id = payload["zone_id"]
            return payload["id"]
        except xmlrpclib.Fault as err:
            raise AuthenticationError(f"Failed to authenticate: '{err}'")

    # Create record. If record already exists with the same content, do nothing.
    def create_record(self, rtype, name, content, ttl):
        """Creates a record for the domain in a new Gandi zone."""
        version = None
        ret = False

        # This isn't quite "do nothing" if the record already exists.
        # In this case, no new record will be created, but a new zone version
        # will be created and set.
        try:
            version = self._api.domain.zone.version.new(self._api_key, self._zone_id)
            self._api.domain.zone.record.add(
                self._api_key,
                self._zone_id,
                version,
                {"type": rtype.upper(), "name": name, "value": content, "ttl": ttl},
            )
            self._api.domain.zone.version.set(self._api_key, self._zone_id, version)
            ret = True

        finally:
            if not ret and version is not None:
                self._api.domain.zone.version.delete(
                    self._api_key, self._zone_id, version
                )

        LOGGER.debug("create_record: %s", ret)
        return ret

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, rtype=None, name=None, content=None):
        """List all record for the domain in the active Gandi zone."""
        opts = {}
        if rtype is not None:
            opts["type"] = rtype.upper()
        if name is not None:
            opts["name"] = self._relative_name(name)
        if content is not None:
            opts["value"] = (
                self._txt_encode(content) if opts.get("type", "") == "TXT" else content
            )

        records = []
        payload = self._api.domain.zone.record.list(
            self._api_key, self._zone_id, 0, opts
        )
        for record in payload:
            processed_record = {
                "type": record["type"],
                "name": self._full_name(record["name"]),
                "ttl": record["ttl"],
                "content": record["value"],
                "id": record["id"],
            }

            # Gandi will add quotes to all TXT record strings
            if processed_record["type"] == "TXT":
                processed_record["content"] = self._txt_decode(
                    processed_record["content"]
                )

            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    # Update a record. Identifier or type+name+content
    def update_record(self, identifier, rtype=None, name=None, content=None):
        """Updates the specified record in a new Gandi zone."""
        if not identifier:
            records = self.list_records(rtype, name)
            if len(records) == 1:
                identifier = records[0]["id"]
            elif len(records) > 1:
                raise Exception("Several record identifiers match the request")
            else:
                raise Exception("Record identifier could not be found")

        identifier = str(identifier)
        version = None

        # Gandi doesn't allow you to edit records on the active zone file.
        # Gandi also doesn't persist zone record identifiers when creating
        # a new zone file. To update by identifier, we lookup the record
        # by identifier, then use the record fields to find the record in
        # the newly created zone.
        records = self._api.domain.zone.record.list(
            self._api_key, self._zone_id, 0, {"id": identifier}
        )

        if len(records) == 1:
            rec = records[0]
            del rec["id"]

            try:
                version = self._api.domain.zone.version.new(
                    self._api_key, self._zone_id
                )
                records = self._api.domain.zone.record.list(
                    self._api_key, self._zone_id, version, rec
                )
                if len(records) != 1:
                    raise self.GandiInternalError("expected one record")

                if rtype is not None:
                    rec["type"] = rtype.upper()
                if name is not None:
                    rec["name"] = self._relative_name(name)
                if content is not None:
                    rec["value"] = (
                        self._txt_encode(content) if rec["type"] == "TXT" else content
                    )

                records = self._api.domain.zone.record.update(
                    self._api_key, self._zone_id, version, {"id": records[0]["id"]}, rec
                )
                if len(records) != 1:
                    raise self.GandiInternalError("Expected one updated record")

                self._api.domain.zone.version.set(self._api_key, self._zone_id, version)
                ret = True

            except self.GandiInternalError:
                pass

            finally:
                if not ret and version is not None:
                    self._api.domain.zone.version.delete(
                        self._api_key, self._zone_id, version
                    )

        LOGGER.debug("update_record: %s", ret)
        return ret

    # Delete existing records.
    # If records do not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """Removes the specified records in a new Gandi zone."""
        version = None
        ret = False

        opts = {}
        if identifier is not None:
            opts["id"] = identifier
        else:
            if not rtype and not name and not content:
                raise ValueError(
                    "Error, at least one parameter from type, name or content must be set"
                )
            if rtype:
                opts["type"] = rtype.upper()
            if name:
                opts["name"] = self._relative_name(name)
            if content:
                opts["value"] = (
                    self._txt_encode(content) if opts["type"] == "TXT" else content
                )

        records = self._api.domain.zone.record.list(
            self._api_key, self._zone_id, 0, opts
        )

        if records:
            try:
                version = self._api.domain.zone.version.new(
                    self._api_key, self._zone_id
                )
                for record in records:
                    del record["id"]
                    self._api.domain.zone.record.delete(
                        self._api_key, self._zone_id, version, record
                    )
                self._api.domain.zone.version.set(self._api_key, self._zone_id, version)
                ret = True
            finally:
                if not ret and version is not None:
                    self._api.domain.zone.version.delete(
                        self._api_key, self._zone_id, version
                    )

        LOGGER.debug("delete_record: %s", ret)
        return ret

    @staticmethod
    def _txt_encode(val):
        if not val:
            return None
        return "".join(['"', val.replace("\\", "\\\\").replace('"', '\\"'), '"'])

    @staticmethod
    def _txt_decode(val):
        if not val:
            return None
        if len(val) > 1 and val[0:1] == '"':
            val = val[1:-1].replace('" "', "").replace('\\"', '"').replace("\\\\", "\\")
        return val

    # This exception is for cleaner handling of internal errors
    # within the Gandi provider codebase
    class GandiInternalError(Exception):
        """Internal exception handling class for Gandi management errors"""
