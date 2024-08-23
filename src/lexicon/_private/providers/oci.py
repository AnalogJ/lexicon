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
from argparse import ArgumentParser
from pathlib import Path
from typing import List

import requests

from lexicon.exceptions import AuthenticationError, LexiconError
from lexicon.interfaces import Provider as BaseProvider

# oci is an optional dependency of lexicon; do not throw an ImportError if
# the dependency is unmet.
try:
    from oci._vendor.requests.exceptions import ConnectTimeout  # type: ignore
    from oci.auth.signers import InstancePrincipalsSecurityTokenSigner  # type: ignore
    from oci.config import from_file  # type: ignore
    from oci.exceptions import ConfigFileNotFound  # type: ignore
    from oci.exceptions import InvalidConfig, ProfileNotFound
    from oci.signer import Signer  # type: ignore
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

CONFIG_VARS = {
    "user",
    "tenancy",
    "fingerprint",
    "key_file",
    "key_content",
    "pass_phrase",
}


class Provider(BaseProvider):
    """
    Provider class for Oracle Cloud Infrastructure DNS
    """

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["dns.oraclecloud.net"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.description = """
        Oracle Cloud Infrastructure (OCI) DNS provider
        """
        parser.add_argument(
            "--auth-config-file",
            help="The full path including filename to an OCI configuration file.",
        )
        parser.add_argument(
            "--auth-profile",
            help="The name of the profile to use (case-sensitive).",
        )
        parser.add_argument(
            "--auth-user",
            help="The OCID of the user calling the API.",
        )
        parser.add_argument(
            "--auth-tenancy",
            help="The OCID of your tenancy.",
        )
        parser.add_argument(
            "--auth-fingerprint",
            help="The fingerprint for the public key that was added to the calling user.",
        )
        parser.add_argument(
            "--auth-key-content",
            help="The full content of the calling user's private signing key in PEM format.",
        )
        parser.add_argument(
            "--auth-key-file",
            help="The full path including filename to the calling user's private signing key in PEM format.",
        )
        parser.add_argument(
            "--auth-pass-phrase",
            help="If the private key is encrypted, the pass phrase must be provided.",
        )
        parser.add_argument(
            "--auth-region",
            help="An OCI region identifier. Select the closest region for best performance.",
        )
        parser.add_argument(
            "--auth-type",
            help="Valid options are 'api_key' (default) or 'instance_principal'.",
        )

    def __init__(self, config):
        """Initialize OCI DNS client."""
        super(Provider, self).__init__(config)
        self.domain_id = None
        self._signer = None

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

        if auth_type == "instance_principal":
            try:
                self._signer = InstancePrincipalsSecurityTokenSigner()
                region = self._signer.region
            except ConnectTimeout:
                raise

        else:
            oci_config = {}
            try:
                oci_config = from_file(
                    file_location=file_location, profile_name=profile_name
                )
            except (ConfigFileNotFound, ProfileNotFound):
                for var in CONFIG_VARS:
                    if os.environ.get(f"OCI_CLI_{var.upper()}"):
                        oci_config[var] = os.environ.get(f"OCI_CLI_{var.upper()}")

                    if self._get_provider_option(f"auth_{var}"):
                        oci_config[var] = self._get_provider_option(f"auth_{var}")

            region = (
                self._get_provider_option("auth_region")
                if self._get_provider_option("auth_region")
                else "us-ashburn-1"
            )
            if hasattr(oci_config, "region") is False:
                oci_config["region"] = region

            try:
                self._signer = Signer.from_config(oci_config)
            except InvalidConfig:
                raise

        self.endpoint = f"https://dns.{region}.oraclecloud.com/20180115"
        LOGGER.debug(f"Activated OCI provider with endpoint: {self.endpoint}")

    def authenticate(self):
        try:
            zone = self._get(f"/zones/{self.domain}")
            self.domain_id = zone["id"]
            self.zone_name = zone["name"]
        except requests.exceptions.HTTPError as e:
            LOGGER.error(
                f"Error: invalid zone or permission denied accessing {self.domain}"
            )
            raise AuthenticationError(e)

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing
    def create_record(self, rtype, name, content):
        name = self._full_name(name)
        patchset = {
            "items": [
                {
                    "operation": "ADD",
                    "domain": name,
                    "rtype": rtype,
                    "rdata": content,
                    "ttl": (
                        self._get_lexicon_option("ttl")
                        if self._get_lexicon_option("ttl")
                        else None
                    ),
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
    def list_records(self, rtype=None, name=None, content=None):
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
    def update_record(self, identifier, rtype=None, name=None, content=None):
        name = self._full_name(name) if name else None
        if identifier:
            records = [
                record
                for record in self.list_records(rtype=rtype)
                if identifier == record["id"]
            ]
        else:
            records = self.list_records(rtype=rtype, name=name)

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
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        name = self._full_name(name) if name else None
        if not identifier and not content:
            try:
                records = self.list_records(rtype, name)
                if len(records) > 0:
                    self._delete(f"/zones/{self.zone_name}/records/{name}/{rtype}")
                    LOGGER.debug(f"OCI: deleted {rtype} recordset for {name}.")
                else:
                    return True
            except requests.exceptions.HTTPError:
                raise LexiconError(f"OCI Error deleting {rtype} recordset for {name}")

        else:
            records = self.list_records(rtype=rtype, name=name, content=content)

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
            auth=self._signer,
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
