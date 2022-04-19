"""
Notes on this Provider

1. Make sure the NIOS Version support WAPI 2.6.1
2. Have a valid Certificate from a public CA installed at the Infoblox

Commandline examples:
1. all parameters given:
lexicon infoblox --ib-host myib.mydomain.tld --auth-user {username} --auth-psw {passwordd}
    --ib-view default create test.local A --content 10.10.10.11 --name lexicon1
2. Parameters mixed with ENV
LEXICON_INFOBLOX_AUTH_USER={user} LEXICON_INFOBLOX_AUTH_PSW={password} lexicon infoblox
    --ib-host myib.mydomain.tld --ib-view default create test.local A
    --content 10.10.10.11 --name lexicon1

"""
import json
import logging

import requests

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["test.local."]
# SOA and NS are not record types itself, but rather auto created depending on the Zone settings.
# Either Primary Grid Member directly assigned to the zone, or through a ns_group
# skipping for now
"""
Dictionary to map the record Type to different Infoblox specific values
IB_TYPE2CONTENT = {
    'type':['WAPI atribute field content','WAPI base URL per type','WAPI returnfields'],
}
"""
IB_TYPE2CONTENT = {
    "A": ["ipv4addr", "record:a", ",ttl,use_ttl"],
    "AAAA": ["ipv6addr", "record:aaaa", ",ttl,use_ttl"],
    "CNAME": ["canonical", "record:cname", ",ttl,use_ttl"],
    "MX": ["mail_exchanger", "record:mx", ",ttl,use_ttl"],
    "TXT": ["text", "record:txt", ",ttl,use_ttl"],
    "SRV": ["target", "record:srv", ",ttl,use_ttl"],
}


def provider_parser(subparser):
    """Configure provider parser for Infoblox"""
    subparser.add_argument(
        "--auth-user", help="specify the user to access the Infoblox WAPI"
    )
    subparser.add_argument(
        "--auth-psw", help="specify the password to access the Infoblox WAPI"
    )
    subparser.add_argument(
        "--ib-view",
        default="default",
        help="specify DNS View to manage at the Infoblox",
    )
    subparser.add_argument("--ib-host", help="specify Infoblox Host exposing the WAPI")


class Provider(BaseProvider):
    """Provider class for Infoblox"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        # In Case .local. Domains are used, ignore the tldextract in client.py
        # this will be used in test_infoblox.py as well
        if self.config.resolve("lexicon:domain") in NAMESERVER_DOMAINS[0]:
            self.domain = NAMESERVER_DOMAINS[0].rstrip(".")
        self.domain_id = None
        self.version_id = None
        self.view = self._get_provider_option("ib_view")
        self.session = requests.session()
        self.session.auth = (
            self._get_provider_option("auth_user"),
            self._get_provider_option("auth_psw"),
        )
        self.version = "2.6.1"  # WAPI version supported by NIOS 8.3 and above
        self.session.headers.update({"Content-Type": "application/json"})
        self.api_endpoint = (
            f"https://{self._get_provider_option('ib_host')}/wapi/v{self.version}/"
        )

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider,
    # so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason,
    # of if the domain does not exist.
    def _authenticate(self):
        response = self.session.get(
            f"{self.api_endpoint}zone_auth?fqdn={self.domain}&view={self.view}"
        )
        domains = response.json()
        try:
            self.domain_id = domains[0]["_ref"]
        except IndexError:
            LOGGER.error("Domain %s not found in view", self.domain)
            raise AuthenticationError(f"Domain {self.domain} not found in view")

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        if name:
            name = self._fqdn_name(name)
        else:
            raise Exception("Name not specified, no FQDN could be build")
        # Find existing records for all types
        existing = []
        for rrtype in IB_TYPE2CONTENT:
            existing = existing + self._list_records(rtype=rrtype, name=name)
        # we don't want to delete all existing A,AAAA,TXT,SRV,MX,NS records
        # which can not co-exist with CNAMEs
        if any(d["type"] == rtype for d in existing):
            # no conflict in types
            if any(d["content"] == content and d["type"] == rtype for d in existing):
                # already exists
                return True
            if rtype == "CNAME":
                # we found a CNAME entry; we update it with the new target
                return self._update_record_internal(
                    existing[0]["id"], rtype, name, content
                )
            return self._create_record_internal(rtype, name, content)
        if any(d["type"] == "CNAME" and rtype != "CNAME" for d in existing):
            # we found a CNAME entry; we can delete it and create the requested type
            if self._delete_record(identifier=existing[0]["id"]):
                return self._create_record_internal(rtype, name, content)
            LOGGER.error("Deleting record failed for:%s", existing[0]["id"])
            return False
        if any(d["type"] != "CNAME" and rtype == "CNAME" for d in existing):
            LOGGER.error("CNAME requested, but other records already exists")
            raise Exception("CNAME requested, but other records already exists")
        return self._create_record_internal(rtype, name, content)

    def _create_record_internal(self, rtype, name, content):
        if name:
            name = self._fqdn_name(name)
        else:
            raise Exception("Name not specified, no FQDN could be build")
        if rtype.upper() in IB_TYPE2CONTENT:
            uri = self.api_endpoint + IB_TYPE2CONTENT[rtype.upper()][1]
            payload = self._generate_payload(rtype, name, content)
            try:
                response = self.session.post(uri, data=json.dumps(payload))
            except BaseException:
                LOGGER.error("Connection Error during create")
                raise Exception("Connection Error")
            if response.status_code == 201:
                return True
            return False
        raise Exception("RR Type not supported by Infoblox")

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        # Infoblox stores entries based on their type, if type is not specified look up all types
        if not rtype:
            records = []
            for one_rtype in IB_TYPE2CONTENT:
                records = records + self._list_records_internal(
                    rtype=one_rtype, name=name, content=content
                )
            return records
        return self._list_records_internal(rtype=rtype, name=name, content=content)

    def _list_records_internal(self, rtype=None, name=None, content=None):
        # infoblox expect the fullname when looking it up without trailing dot
        if name:
            name = self._fqdn_name(name)
        else:
            name = self.domain
        records = []
        if rtype.upper() in IB_TYPE2CONTENT:
            uri = "{0}{1}?name={2}&view={3}&_return_fields={4}{5}".format(
                self.api_endpoint,
                IB_TYPE2CONTENT[rtype.upper()][1],
                name,
                self.view,
                IB_TYPE2CONTENT[rtype.upper()][0],
                IB_TYPE2CONTENT[rtype.upper()][2],
            )
            try:
                response = self.session.get(uri)
            except BaseException:
                raise Exception("Connection Error")

            results = response.json()
            for result in results:
                if content:
                    # return exact match
                    if (
                        str(content).lower()
                        == str(result[IB_TYPE2CONTENT[rtype][0]]).lower()
                    ):
                        if result["use_ttl"]:
                            record = {
                                "type": rtype,
                                "name": name,
                                "ttl": result["ttl"],
                                "content": result[IB_TYPE2CONTENT[rtype][0]],
                                "id": result["_ref"],
                            }
                        else:
                            record = {
                                "type": rtype,
                                "name": name,
                                "ttl": 3600,  # replace by Infoblox default TTL
                                "content": result[IB_TYPE2CONTENT[rtype][0]],
                                "id": result["_ref"],
                            }
                        records.append(record)
                else:
                    # return any record
                    if result["use_ttl"]:
                        record = {
                            "type": rtype,
                            "name": name,
                            "ttl": result["ttl"],
                            "content": result[IB_TYPE2CONTENT[rtype][0]],
                            "id": result["_ref"],
                        }
                    else:
                        record = {
                            "type": rtype,
                            "name": name,
                            "ttl": 3600,  # replace by Infoblox default TTL
                            "content": result[IB_TYPE2CONTENT[rtype][0]],
                            "id": result["_ref"],
                        }
                    records.append(record)
            return records
        return records

    # Update a record. Identifier must be specified.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        if identifier:
            return self._update_record_internal(
                identifier=identifier, rtype=rtype, name=name, content=content
            )
        success = []
        for record in self._list_records(rtype, name, content):
            success.append(
                self._update_record_internal(
                    identifier=record["id"], rtype=rtype, name=name, content=content
                )
            )
        if False in success:
            return False
        return True

    def _update_record_internal(self, identifier, rtype=None, name=None, content=None):
        uri = self.api_endpoint + identifier
        payload = self._generate_payload(rtype, name, content)
        # remove view and name from the payload, as they can not be updated
        del payload["view"]
        del payload["name"]
        try:
            response = self.session.put(uri, data=json.dumps(payload))
        except BaseException:
            LOGGER.error("Connection Error during create")
            raise Exception("Connection Error")
        if response.status_code == 200:
            return True
        return False

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        # Infoblox Object Identifier example:
        # record:cname/ZG5zLmJpbmRfY25hbWUkLjIzLmRlLm1naS5sZXhpY29uNA:lexicon.domain.tld/view
        if identifier:
            return self._delete_record_internal(identifier)
        success = []
        for record in self._list_records(rtype, name, content):
            success.append(self._delete_record_internal(record["id"]))
        if False in success:
            return False
        return True

    def _delete_record_internal(self, identifier=None):
        if identifier:
            uri = f"{self.api_endpoint}{identifier}"
            try:
                response = self.session.delete(uri)
            except BaseException:
                LOGGER.error("Connection Error during create")
                raise Exception("Connection Error")
            if response.status_code == 200:
                return True
            return False
        return False

    # Helpers
    def _generate_payload(self, rtype, name, content):
        # build full object as required by Infoblox WAPI
        payload = {}
        payload["view"] = self.view
        payload["name"] = name
        if rtype.upper() == "TXT":
            payload[IB_TYPE2CONTENT[rtype.upper()][0]] = '"' + content + '"'
        else:
            payload[IB_TYPE2CONTENT[rtype.upper()][0]] = content
        if self._get_lexicon_option("ttl"):
            payload["ttl"] = self._get_lexicon_option("ttl")
            payload["use_ttl"] = True
        # MX and SRV have additional fields
        if rtype.upper() == "MX":
            payload["preference"] = self._get_lexicon_option("priority")
        elif rtype.upper() == "SRV":
            payload["priority"] = self._get_lexicon_option("priority")
            payload["weight"] = self._get_provider_option("ib_weight")
            payload["port"] = self._get_provider_option("ib_port")
        return payload

    def _fqdn_name(self, record_name):
        record_name = record_name.rstrip(
            "."
        )  # strip trailing period from fqdn if present
        # check if the record_name is fully specified
        if not record_name.endswith(self.domain):
            record_name = f"{record_name}.{self.domain}"
        return f"{record_name}"  # return the fqdn name without trailing dot

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # Helper _request is not used in Infoflox provider
        pass
