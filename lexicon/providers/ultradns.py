"""
Lexicon UltraDNS Provider

Derived from PowerDNS provider

API Docs: https://doc.ultradns.com/md/httpapi/api_spec/

Implementation notes:
* The UltraDNS API does not assign a unique identifier to each record in the way
that Lexicon expects. We work around this by creating an ID based on the record
name, type and content, which when taken together are always unique
* The UltraDNS API has no notion of 'create a single record' or 'delete a single
record'. All operations are either 'replace the RRSet with this new set of records'
or 'delete all records for this name and type. Similarly, there is no notion of
'change the content of this record', because records are identified by their name,
type and content.
* The API is very picky about the format of values used when creating records:
** CNAMEs must be fully qualified
This is why the _clean_content and _unclean_content methods exist, to convert
back and forth between the format UltraDNS expects, and the format Lexicon uses
"""
import hashlib
import json
import logging

import requests

from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["ultradns.net"]


def provider_parser(subparser):
    """Configure provider parser for ultradns"""
    subparser.add_argument(
        "--auth-token",
        help="specify token for authentication;"
        + " if not set --auth-token, --auth-password are used",
    )
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )


class Provider(BaseProvider):
    """Provider class for UltraDNS"""

    def __init__(self, config):
        super(Provider, self).__init__(config)

        self.api_key = self._get_provider_option("auth_token")

        assert (self.api_key is not None) or (
            self._get_provider_option("auth_username") is not None
            and self._get_provider_option("auth_password") is not None
        )

    def zone_data(self):
        """Get zone data"""
        data = self._get("/zones/" + self._ensure_dot(self.domain) + "/rrsets").json()
        for i, rrset in enumerate(data["rrSets"]):
            data["rrSets"][i]["rrtype"] = self._clean_rrtype(rrset["rrtype"])
        return data

    def _authenticate(self):
        if self.api_key is None:
            username = self._get_provider_option("auth_username")
            password = self._get_provider_option("auth_password")
            url = "https://restapi.ultradns.com/v2/authorization/token"
            data = {
                "grant_type": "password",
                "username": username,
                "password": password,
            }

            result = requests.post(url, data=data)
            result.raise_for_status()
            self.api_key = result.json()["accessToken"]

        assert self.api_key is not None
        self.domain_id = self.domain
        # Test auth works
        self.zone_data()

    def _make_identifier(self, rtype, name, content):
        sha256 = hashlib.sha256()
        sha256.update(("type=" + rtype + ",").encode("utf-8"))
        sha256.update(("name=" + name + ",").encode("utf-8"))
        sha256.update(("data=" + content + ",").encode("utf-8"))
        return sha256.hexdigest()[0:7]

    def _list_records(self, rtype=None, name=None, content=None):
        records = []
        for rrset in self.zone_data()["rrSets"]:
            if (
                name is None
                or self._fqdn_name(rrset["ownerName"]) == self._fqdn_name(name)
            ) and (rtype is None or rrset["rrtype"] == rtype):
                for record in rrset["rdata"]:
                    if content is None or record == self._clean_content(rtype, content):
                        records.append(
                            {
                                "type": rrset["rrtype"],
                                "name": self._full_name(rrset["ownerName"]),
                                "ttl": rrset["ttl"],
                                "content": self._unclean_content(
                                    rrset["rrtype"], record
                                ),
                                "id": self._make_identifier(
                                    rrset["rrtype"], rrset["ownerName"], record
                                ),
                            }
                        )
        LOGGER.debug("list_records: %s", records)
        return records

    def _clean_rrtype(self, rtype):
        """ UltraDNS returns records with types like 'MX (15)' """
        return rtype.split()[0]

    def _clean_content(self, rtype, content):
        if rtype == "CNAME" and not content.endswith("."):
            # Regularise non-FQDN CNAMEs - do not affect FQDNs or we break out of zone
            content = self._fqdn_name(content)
        return content

    def _unclean_content(self, rtype, content):
        if rtype == "CNAME" and not content.endswith("."):
            # Regularise non-FQDN CNAMEs - do not affect FQDNs or we break out of zone
            content = self._full_name(content)
        return content

    def _create_record(self, rtype, name, content):
        rname = self._fqdn_name(name)
        newcontent = self._clean_content(rtype, content)

        updated_data = {
            "ownerName": rname,
            "rrtype": rtype,
            "rdata": [],
            "ttl": self._get_lexicon_option("ttl") or 600,
        }

        updated_data["rdata"].append(newcontent)

        found = False
        for rrset in self.zone_data()["rrSets"]:
            if rrset["ownerName"] == rname and rrset["rrtype"] == rtype:
                updated_data["ttl"] = rrset["ttl"]
                found = True

                for record in rrset["rdata"]:
                    if record == newcontent:
                        return True  # Exactly the same record exists, just return
                    updated_data["rdata"].append(record)
                break

        if found:
            self._put(
                f"/zones/{self._ensure_dot(self.domain)}/rrsets/{rtype}/{rname}",
                data=updated_data,
            )
        else:
            self._post(
                f"/zones/{self._ensure_dot(self.domain)}/rrsets/{rtype}/{rname}",
                data=updated_data,
            )

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):

        data = self.zone_data()

        if identifier is not None:
            found = False
            for rrset in data["rrSets"]:
                for record in rrset["rdata"]:
                    ident = self._make_identifier(
                        rrset["rrtype"], rrset["ownerName"], record
                    )
                    if identifier == ident:
                        rtype = rrset["rrtype"]
                        name = self._full_name(rrset["ownerName"])
                        content = self._unclean_content(rrset["rrtype"], record)
                        found = True
                        break
                else:
                    continue
                break  # break out of the outer loop too
            if not found:
                return True  # No match means nothing to do

        LOGGER.debug("delete %s %s %s", rtype, name, content)
        if rtype is None or name is None:
            raise Exception("Must specify at least both rtype and name")

        rname = self._fqdn_name(name)

        found = False
        for rrset in data["rrSets"]:
            if (
                rrset["rrtype"] == rtype
                and self._fqdn_name(rrset["ownerName"]) == rname
            ):
                update_data = rrset
                found = True

                if content is None:
                    update_data["rdata"] = []
                else:
                    new_record_list = []
                    for record in update_data["rdata"]:
                        if self._clean_content(rrset["rrtype"], content) != record:
                            new_record_list.append(record)

                    update_data["rdata"] = new_record_list
                break

        if not found:
            return True  # Do nothing if the record did not exist

        request = {"rrSets": [update_data]}
        LOGGER.debug("request: %s", request)

        if update_data["rdata"]:
            self._put(
                f"/zones/{self._ensure_dot(self.domain)}/rrsets/{rtype}/{rname}",
                data=update_data,
            )
        else:
            self._delete(
                f"/zones/{self._ensure_dot(self.domain)}/rrsets/{rtype}/{rname}"
            )

        return True

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        self._delete_record(identifier, rtype, name, content)
        return self._create_record(rtype, name, content)

    def _patch(self, url="/", data=None, query_params=None):
        return self._request("PATCH", url, data=data, query_params=query_params)

    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        response = requests.request(
            action,
            "https://restapi.ultradns.com/v2" + url,
            params=query_params,
            data=json.dumps(data),
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        LOGGER.debug("response: %s", response.text)
        response.raise_for_status()
        return response

    @classmethod
    def _ensure_dot(cls, text):
        """
        This function makes sure a string contains a dot at the end
        """
        if text.endswith("."):
            return text
        return text + "."
