# coding: utf-8
# Copyright (c) 2016, Jason Kulatunga
# Copyright (c) 2021, Oracle and/or its affiliates.
"""
The Oracle Cloud Infrastructure (OCI) provider can create, list, update and
delete records in any public DNS zone hosted in a tenancy located in any
region within the OCI commercial (OC1) realm.

No authentication details are required if the OCI CLI installed and the DEFAULT
profile configured in the ~/.oci/config file has the appropriate permission for
the target DNS zone or the equivalent OCI_CLI environment variables are set.

Otherwise, you can either set the required LEXICON_OCI_AUTH_* environment
variables or pass the required --auth-* command-line parameters. If you do not
have a configuration file, you must provide user, tenancy, region, key and
fingerprint details.

Set the --auth-type parameter to 'instance_principal' to use instance principal
authentication when running Lexicon on an Oracle Cloud Infrastructure compute
instance. This method requires permission to be granted via IAM policy to a
dynamic group that includes the compute instance.

See https://docs.oracle.com/en-us/iaas/Content/DNS/Concepts/dnszonemanagement.htm
for in-depth documentation on managing DNS via the OCI console, SDK or API.
"""
import logging
import os
from pathlib import Path

import requests

from lexicon.exceptions import LexiconError
from lexicon.providers.base import Provider as BaseProvider

# oci is an optional dependency of lexicon; do not throw an ImportError if
# the dependency is unmet.
try:
    from oci.auth.signers import InstancePrincipalsSecurityTokenSigner  # type: ignore
    from oci.config import from_file, validate_config  # type: ignore
    from oci.exceptions import ConfigFileNotFound  # type: ignore
    from oci.exceptions import InvalidConfig, ProfileNotFound  # type: ignore
    from oci.signer import Signer  # type: ignore
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["dns.oraclecloud.net"]

CONFIG_VARS = {
    "user",
    "tenancy",
    "fingerprint",
    "key_file",
    "key_content",
    "pass_phrase",
    "region",
}


def provider_parser(subparser):
    """Generate a subparser for Oracle Cloud Infrastructure DNS"""
    subparser.description = """
    Oracle Cloud Infrastructure (OCI) DNS provider
    """
    subparser.add_argument(
        "--auth-config-file",
        help="The full path including filename to an OCI configuration file.",
    )
    subparser.add_argument(
        "--auth-user",
        help="The OCID of the user calling the API.",
    )
    subparser.add_argument(
        "--auth-tenancy",
        help="The OCID of your tenancy.",
    )
    subparser.add_argument(
        "--auth-fingerprint",
        help="The fingerprint for the public key that was added to the calling user.",
    )
    subparser.add_argument(
        "--auth-key-content",
        help="The full content of the calling user's private signing key in PEM format.",
    )
    subparser.add_argument(
        "--auth-pass-phrase",
        help="If the private key is encrypted, the pass phrase must be provided.",
    )
    subparser.add_argument(
        "--auth-region",
        help="The home region of your tenancy.",
    )
    subparser.add_argument(
        "--auth-type",
        help="Valid options are 'api_key' (default) or 'instance_principal'.",
    )


class Provider(BaseProvider):
    """
    Provider class for Oracle Cloud Infrastructure DNS
    """

    def __init__(self, config):
        """Initialize OCI DNS client."""
        super(Provider, self).__init__(config)
        self.domain_id = None

        file_location = (
            self._get_provider_option("auth_config_file")
            if self._get_provider_option("auth_config_file")
            else str(Path(Path.home() / ".oci" / "config"))
        )
        profile_name = (
            self._get_provider_option("auth_profile")
            if self._get_provider_option("auth_profile")
            else "DEFAULT"
        )
        auth_type = (
            self._get_provider_option("auth_type")
            if self._get_provider_option("auth_type")
            else "api_key"
        )

        signer = (
            InstancePrincipalsSecurityTokenSigner()
            if auth_type == "instance_principal"
            else None
        )

        oci_config = {}
        try:
            oci_config = from_file(
                file_location=file_location, profile_name=profile_name
            )
        except (ConfigFileNotFound, ProfileNotFound):
            pass

        for var in CONFIG_VARS:
            if os.environ.get(f"OCI_CLI_{var.upper()}"):
                oci_config[var] = os.environ.get(f"OCI_CLI_{var.upper()}")

            if self._get_provider_option(f"auth_{var}"):
                oci_config[var] = self._get_provider_option(f"auth_{var}")

            if var not in oci_config.keys():
                oci_config[var] = None

        try:
            validate_config(oci_config)
        except InvalidConfig:
            raise

        self.auth = (
            signer
            if signer
            else Signer(
                oci_config["tenancy"],
                oci_config["user"],
                oci_config["fingerprint"],
                oci_config["key_file"],
                oci_config["pass_phrase"],
                oci_config["key_content"],
            )
        )

        self.endpoint = f"https://dns.{oci_config['region']}.oraclecloud.com/20180115"
        LOGGER.debug(f"Activated OCI provider with endpoint: {self.endpoint}")

    def _authenticate(self):
        try:
            zone = self._get(f"/zones/{self.domain}")
            self.domain_id = zone["id"]
            self.zone_name = zone["name"]
        except requests.exceptions.HTTPError:
            LOGGER.error(
                f"Error: invalid zone or permission denied accessing {self.domain}"
            )
            raise

    # Create record. If record already exists with the same content, do nothing
    def _create_record(self, rtype, name, content):

        name = self._full_name(name)
        patchset = {
            "items": [
                {
                    "operation": "ADD",
                    "rtype": rtype,
                    "rdata": content,
                    "ttl": self._get_lexicon_option("ttl")
                    if self._get_lexicon_option("ttl")
                    else None,
                }
            ]
        }

        try:
            self._patch(f"/zones/{self.zone_name}/records/{name}", patchset)
            LOGGER.debug(f"OCI: created new {rtype} record for {name}.")
        except requests.exceptions.HTTPError:
            raise LexiconError("OCI Error: record not created.")

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):

        query_params = {"limit": 100, "rtype": rtype}
        name = self._full_name(name) if name else None

        if name:
            payload = self._get(f"/zones/{self.zone_name}/records/{name}", query_params)
        else:
            payload = self._get(f"/zones/{self.zone_name}/records", query_params)

        records = []
        for item in payload["items"]:
            rdata = item["rdata"].strip('"')
            name = self._full_name(item["domain"])
            if content and content != rdata:
                continue

            record = {
                "type": item["rtype"],
                "name": name,
                "ttl": item["ttl"],
                "content": rdata,
                "id": item["recordHash"],
            }
            records.append(record)

        LOGGER.debug(
            f"OCI: listing {len(records)} {rtype} records from {self.zone_name}."
        )
        return records

    # Update a record. Identifier must be specified.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        name = self._full_name(name) if name else None
        if identifier:
            records = [
                record
                for record in self._list_records(rtype=rtype)
                if identifier == record["id"]
            ]
        else:
            records = self._list_records(rtype=rtype, name=name)

        if not records:
            raise LexiconError(
                f"OCI Error: unable to find {rtype} record for {name} to update."
            )
        elif len(records) > 1:
            LOGGER.warning(
                f"Warning: multiple {rtype} records found for {name} containing {content}. Updating the first record returned.",
            )

        identifier = records[0]["id"]
        domain = self._full_name(records[0]["name"])
        ttl = (
            self._get_lexicon_option("ttl") if self._get_lexicon_option("ttl") else None
        )

        patchset = {
            "items": [
                {"operation": "REMOVE", "recordHash": identifier},
                {"operation": "ADD", "rtype": rtype, "rdata": content, "ttl": ttl},
            ]
        }

        try:
            self._patch(f"/zones/{self.zone_name}/records/{domain}", patchset)
            LOGGER.debug(f"OCI: updated {rtype} record [{identifier}].")
        except requests.exceptions.HTTPError:
            raise LexiconError(f"OCI Error updating {rtype} record for {domain}")

        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):

        name = self._full_name(name) if name else None
        if not identifier and not content:
            try:
                records = self._list_records(rtype, name)
                if len(records) > 0:
                    self._delete(f"/zones/{self.zone_name}/records/{name}/{rtype}")
                    LOGGER.debug(f"OCI: deleted {rtype} recordset for {name}.")
                else:
                    return True
            except requests.exceptions.HTTPError:
                raise LexiconError(f"OCI Error deleting {rtype} recordset for {name}")

        else:
            records = self._list_records(rtype=rtype, name=name, content=content)

            if identifier:
                records = [record for record in records if record["id"] == identifier]

            if len(records) == 0:
                return True

            patchset = {
                "items": [
                    {"operation": "REMOVE", "recordHash": record["id"]}
                    for record in records
                ]
            }

            try:
                self._patch(f"/zones/{self.zone_name}/records", patchset)
                LOGGER.debug(f"OCI: deleted {rtype} record(s) from {self.zone_name}.")
            except requests.exceptions.HTTPError:
                raise LexiconError("Error deleting record(s)")

        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):

        if not data and action != "DELETE":
            data = {}

        if not query_params:
            query_params = {}

        if not url.startswith(self.endpoint):
            url = self.endpoint + url

        response = requests.request(
            action,
            url,
            params=query_params,
            auth=self.auth,
            json=data if data else None,
        )
        response.raise_for_status()

        if response.content:
            results = response.json()
        else:
            return None

        # The opc-next-page header indicates there is another page of results
        if "opc-next-page" in response.headers:
            query_params["page"] = response.headers["opc-next-page"]
            response = requests.request(
                action,
                url,
                params=query_params,
                auth=self.auth,
                json=data if data else None,
            )
            response.raise_for_status()
            results += response.json()

        return results
