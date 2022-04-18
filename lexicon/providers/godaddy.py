"""Module provider for Godaddy"""
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry  # type: ignore

from lexicon.exceptions import LexiconError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["godaddy.com", "domaincontrol.com"]


def provider_parser(subparser):
    """Generate a subparser for Godaddy"""
    subparser.add_argument("--auth-key", help="specify the key to access the API")
    subparser.add_argument("--auth-secret", help="specify the secret to access the API")


class Provider(BaseProvider):
    """
    Implements the DNS GoDaddy provider.
    Some general remarks about this provider, because it uses a weirdly designed API.
    Indeed, there is no direct way to insert, update or delete a specific record.
    Furthermore, there is no unique identifier for a record.
    Instead GoDaddy use a replace approach: for a given set of records one
    can replace this set with a new set sent through API.
    For the sake of simplicity and consistency across the provider edit methods,
    the set will be always all records in the DNS zone.
    With this approach:
        - adding a record consists in appending a record to the obtained set and call
          replace with the updated set,
        - updating a record consists in modifying a record in the obtained set and call
          replace with the updated set,
        - deleting a record consists in removing a record in the obtained set and call
          replace with the updated set.
    In parallel, as said before, there is no unique identifier.
    This provider then implement a pseudo-identifier, to allow an easy update or delete
    using the '--identifier' lexicon parameter.
    But you need to call the 'list' command just before executing and update/delete action,
    because identifier value is tied to the content of the record, and will change anytime
    something is changed in the record.
    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.godaddy.com/v1"

    def _authenticate(self):
        domain = self.domain

        result = self._get(f"/domains/{domain}")
        self.domain_id = result["domainId"]

    def _list_records(self, rtype=None, name=None, content=None):
        domain = self.domain

        url = f"/domains/{domain}/records"
        if rtype:
            url += f"/{rtype}"
        if name:
            url += f"/{self._relative_name(name)}"

        raws = self._get(url)

        records = []
        for raw in raws:
            records.append(
                {
                    "id": Provider._identifier(raw),
                    "type": raw["type"],
                    "name": self._full_name(raw["name"]),
                    "ttl": raw["ttl"],
                    "content": raw["data"],
                }
            )

        if content:
            records = [record for record in records if record["data"] == content]

        LOGGER.debug("list_records: %s", records)

        return records

    def _create_record(self, rtype, name, content):
        domain = self.domain
        relative_name = self._relative_name(name)
        ttl = self._get_lexicon_option("ttl")

        # Retrieve existing data in DNS zone.
        records = self._get(f"/domains/{domain}/records/{rtype}/{relative_name}")

        # Check if a record already matches given parameters
        for record in records:
            if record["data"] == content:
                LOGGER.debug(
                    "create_record (ignored, duplicate): %s %s %s", rtype, name, content
                )
                return True

        # Append a new entry corresponding to given parameters.
        data = {"type": rtype, "name": relative_name, "data": content}
        if ttl:
            data["ttl"] = int(ttl)

        records.append(data)

        # Insert the record
        self._put(f"/domains/{domain}/records/{rtype}/{relative_name}", records)

        LOGGER.debug("create_record: %s %s %s", rtype, name, content)

        return True

    def _find_matching_records(
        self,
        identifier: Optional[str],
        rtype: Optional[str],
        name: Optional[str],
        content: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        # Retrieve existing data in DNS zone.
        records = self._get(f"/domains/{self.domain}/records")

        # Find matching record, either by identifier matching, or rtype + name + content matching
        if identifier:
            matching_records = [
                record
                for record in records
                if Provider._identifier(record) == identifier
            ]

            if not matching_records:
                raise LexiconError(
                    f"Could not find record matching identifier: {identifier}"
                )
        else:
            matching_records = records.copy()

            if rtype:
                matching_records = [
                    record for record in matching_records if record["type"] == rtype
                ]

            if name:
                matching_records = [
                    record
                    for record in matching_records
                    if self._relative_name(record["name"]) == self._relative_name(name)
                ]

            if content:
                matching_records = [
                    record for record in matching_records if record["data"] == content
                ]

            if not matching_records:
                suffix = f", content: {content}" if content else ""
                raise LexiconError(
                    f"Could not find record matching type: {rtype}, name: {name}{suffix}"
                )

        return matching_records, records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # No identifier is used with GoDaddy.
        # We can rely either:
        #   - only on rtype/name to get the relevant records, both of them are required
        #     or we will could update to much records ...,
        #   - or by the pseudo-identifier provided
        # Furthermore for rtype/name approach, we cannot update all matching records, as it
        # would lead o an error (two entries of same rtype + name cannot have the same content).
        # So for rtype/name approach, we search first matching record for rtype/name on which
        # content is different, and we update it before synchronizing the DNS zone.
        if not identifier and not rtype:
            raise Exception("ERROR: rtype is required")
        if not identifier and not name:
            raise Exception("ERROR: name is required")

        matching_records, records = self._find_matching_records(
            identifier, rtype, name, None
        )

        if len(matching_records) > 1:
            LOGGER.warn(
                "Warning, multiple matching updatable records found, first one is picked."
            )

        matching_record = matching_records[0]

        # Ensure all content to update is defined
        rtype = rtype if rtype else matching_record["type"]
        name = name if name else matching_record["name"]
        content = content if content else matching_record["data"]
        relative_name = self._relative_name(name)

        # Filter out DNS zone records to focus on the target rtype
        records = [record for record in records if record["type"] == rtype]

        # Prepare update in-place
        matching_record["type"] = rtype
        matching_record["name"] = relative_name
        matching_record["data"] = content

        # Actual update, with two possible strategies
        if self._relative_name(matching_record["name"]) == relative_name:
            # If the name of the record stays the same, we use the scoped API on this name to
            # redefine specifically the records of this rtype and name, including the updated one.
            records = [
                record
                for record in records
                if self._relative_name(record["name"]) == relative_name
            ]
            self._put(
                f"/domains/{self.domain}/records/{rtype}/{relative_name}",
                records,
            )
        else:
            # If the name of the record changes, we redefine the whole set to records of this rtype
            # using the list of records, including the updated one.
            self._put(f"/domains/{self.domain}/records/{rtype}", records)

        LOGGER.debug("update_record: %s %s %s", rtype, name, content)

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        # Get the list of records to evict and the list of all current records in the DNS zone.
        matching_records, records = self._find_matching_records(
            identifier, rtype, name, content
        )

        if identifier:
            # When identifier is used, by definition only one unique record can match.
            rtype = matching_records[0]["type"]
            identifiers = [identifier]
        else:
            identifiers = [self._identifier(record) for record in matching_records]

        # Clean up the records list:
        # - by removing all records that are not matching the target type
        # - by removing all records that must be evicted in the current call
        records = [
            record
            for record in records
            if record["type"] == rtype and self._identifier(record) not in identifiers
        ]

        # Resynchronize the current set of records for the target type using the cleaned list,
        # which effectively deletes the records to evict.
        if records:
            self._put(f"/domains/{self.domain}/records/{rtype}", records)
        else:
            # List records is empty, the intention here is to delete all records of a given type.
            # Sadly GoDaddy API ignores empty arrays in a PUT request, so it is not possible to
            # do that directly using the endpoint `PUT /domains/{domain}/records/{rtype}`.
            # The trick here is to use PUT with one unique record remaining (matching_records[0]),
            # then use the endpoint `DELETE /domains/{domain}/records/{rtype}/{name}` to remove
            # the remaining record.
            self._put(f"/domains/{self.domain}/records/{rtype}", [matching_records[0]])
            self._delete(
                f"/domains/{self.domain}/records/{rtype}/{matching_records[0]['name']}"
            )

        LOGGER.debug("delete_records: %s %s %s", rtype, name, content)

        return True

    # GoDaddy provides no identifier for a record, which is a problem
    # where identifiers can be used (delete and update).
    # To circumvent this, we implement a pseudo-identifier,which is basically
    # a hash of type+name+content of a given record.
    # It is far from perfect, as the identifier will change each time
    # we change something in the record ...
    # But at least, one can use 'lexicon godaddy list ...' then
    # 'lexicon godaddy update --identifier ...' to modify specific record.
    # However, 'lexicon godaddy list ...' should be called each time DNS
    # zone had been changed to calculate new identifiers.
    @staticmethod
    def _identifier(record):
        sha256 = hashlib.sha256()
        sha256.update(("type=" + record.get("type", "") + ",").encode("utf-8"))
        sha256.update(("name=" + record.get("name", "") + ",").encode("utf-8"))
        sha256.update(("data=" + record.get("data", "") + ",").encode("utf-8"))
        return sha256.hexdigest()[0:7]

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # When editing DNS zone, API is unavailable for few seconds
        # (until modifications are propagated).
        # In this case, call to API will return 409 HTTP error.
        # We use the Retry extension to retry the requests until
        # we get a processable response (402 HTTP status, or an HTTP error != 409)
        try:
            retries = Retry(
                total=10,
                backoff_factor=0.5,
                status_forcelist=[409],
                allowed_methods=frozenset(["GET", "PUT", "POST", "DELETE", "PATCH"]),
            )
        except TypeError:
            # Support for urllib3<1.26
            retries = Retry(
                total=10,
                backoff_factor=0.5,
                status_forcelist=[409],
                method_whitelist=frozenset(["GET", "PUT", "POST", "DELETE", "PATCH"]),
            )

        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=retries))

        result = session.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data) if data else None,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                # GoDaddy uses a key/secret pair to authenticate
                "Authorization": f"sso-key {self._get_provider_option('auth_key')}:{self._get_provider_option('auth_secret')}",
            },
        )

        result.raise_for_status()

        try:
            # Return the JSON body response if exists.
            return result.json()
        except ValueError:
            # For some requests command (eg. PUT), GoDaddy will not
            # return any JSON, just an HTTP status without body.
            return None
