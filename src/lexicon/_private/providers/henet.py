"""Module provider for Henet"""
import logging
import re
from argparse import ArgumentParser
from typing import List

from bs4 import BeautifulSoup  # type: ignore
from requests import Session

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """
    he.net provider
    """

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["he.net"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.description = """A provider for Hurricane Electric DNS.
        NOTE: THIS DOES NOT WORK WITH 2-FACTOR AUTHENTICATION.
              YOU MUST DISABLE IT IF YOU'D LIKE TO USE THIS PROVIDER.
        """
        parser.add_argument(
            "--auth-username", help="specify username for authentication"
        )
        parser.add_argument(
            "--auth-password", help="specify password for authentication"
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain = self.domain
        self.domain_id = None
        self.session = None

    def authenticate(self):
        # Create the session GET the login page to retrieve a session cookie
        self.session = Session()
        self.session.get("https://dns.he.net/")

        # Hit the login page with authentication info to login the session
        login_response = self.session.post(
            "https://dns.he.net",
            data={
                "email": self._get_provider_option("auth_username") or "",
                "pass": self._get_provider_option("auth_password") or "",
            },
        )

        # Parse in the HTML, if the div containing the error message is found, error
        html = BeautifulSoup(login_response.content, "html.parser")
        if html.find("div", {"id": "dns_err"}) is not None:
            LOGGER.warning("HE login failed, check HE_USER and HE_PASS")
            return False

        # Make an authenticated GET to the DNS management page
        zones_response = self.session.get("https://dns.he.net")

        html = BeautifulSoup(zones_response.content, "html.parser")
        zone_img = html.find("img", {"name": self.domain, "alt": "delete"})

        # If the tag couldn't be found, error, otherwise, return the value of the tag
        if zone_img is None:
            LOGGER.warning("Domain %s not found in account", self.domain)
            raise AuthenticationError(f"Domain {self.domain} not found in account")

        self.domain_id = zone_img["value"]
        LOGGER.debug("HENET domain ID: %s", self.domain_id)
        return True

    def cleanup(self) -> None:
        pass

    # Create record. If record already exists with the same content, do nothing
    def create_record(self, rtype, name, content):
        LOGGER.debug("Creating record for zone %s", name)
        # Pull a list of records and check for ours
        records = self.list_records(rtype=rtype, name=name, content=content)
        if len(records) >= 1:
            LOGGER.warning("Duplicate record %s %s %s, NOOP", rtype, name, content)
            return True
        data = {
            "account": "",
            "menu": "edit_zone",
            "Type": rtype,
            "hosted_dns_zoneid": self.domain_id,
            "hosted_dns_recordid": "",
            "hosted_dns_editzone": "1",
            "Priority": "",
            "Name": name,
            "Content": content,
            "TTL": "3600",
            "hosted_dns_editrecord": "Submit",
        }
        ttl = self._get_lexicon_option("ttl")
        if ttl:
            if ttl <= 0:
                data["TTL"] = "3600"
            else:
                data["TTL"] = str(ttl)
        prio = self._get_lexicon_option("priority")
        if prio:
            if prio <= 0:
                data["Priority"] = "10"
            else:
                data["Priority"] = str(prio)
        self.session.post("https://dns.he.net/index.cgi", data=data)
        # Pull a list of records and check for ours
        records = self.list_records(name=name)
        if len(records) >= 1:
            LOGGER.info("Successfully added record %s", name)
            return True
        LOGGER.info("Failed to add record %s", name)
        return False

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is
    # received.
    def list_records(self, rtype=None, name=None, content=None):
        return self._list_records_internal(rtype=rtype, name=name, content=content)

    def _list_records_internal(
        self, rtype=None, name=None, content=None, identifier=None
    ):
        records = []
        # Make an authenticated GET to the DNS management page
        edit_response = self.session.get(
            f"https://dns.he.net/?hosted_dns_zoneid={self.domain_id}&menu=edit_zone&hosted_dns_editzone",
        )

        # Parse the HTML response, and list the table rows for DNS records
        html = BeautifulSoup(edit_response.content, "html.parser")

        def is_dns_tr_type(klass):
            return klass and re.compile("dns_tr").search(klass)

        records = html.findAll("tr", class_=is_dns_tr_type)

        # If the tag couldn't be found, error, otherwise, return the value of the tag
        if records is None or not records:
            LOGGER.warning("Domains not found in account")
            return records

        new_records = []
        for dns_tr in records:
            tds = dns_tr.findAll("td")
            # Process HTML in the TR children to derive each object
            rec = {}
            rec["zone_id"] = tds[0].string
            rec["id"] = tds[1].string
            rec["name"] = tds[2].string
            # the 4th entry is a comment
            type_elem = tds[3].find("span", class_="rrlabel")
            rec["type"] = type_elem.string if type_elem else None
            rec["ttl"] = tds[4].string
            if tds[5].string != "-":
                rec["priority"] = tds[5]
            rec["content"] = tds[6].string
            rec["is_dynamic"] = tds[7].string == "1"
            rec = self._clean_TXT_record(rec)
            new_records.append(rec)
        records = new_records
        if identifier:
            LOGGER.debug("Filtering %d records by id: %s", len(records), identifier)
            records = [record for record in records if record["id"] == identifier]
        if rtype:
            LOGGER.debug("Filtering %d records by rtype: %s", len(records), rtype)
            records = [record for record in records if record["type"] == rtype]
        if name:
            LOGGER.debug("Filtering %d records by name: %s", len(records), name)
            if name.endswith("."):
                name = name[:-1]
            records = [record for record in records if name in record["name"]]
        if content:
            LOGGER.debug(
                "Filtering %d records by content: %s", len(records), content.lower()
            )
            records = [
                record
                for record in records
                if record["content"].lower() == content.lower()
            ]
        LOGGER.debug("Final records (%d): %s", len(records), records)

        return records

    # Create or update a record.
    def update_record(self, identifier, rtype=None, name=None, content=None):
        # Delete record if it exists
        self.delete_record(identifier, rtype, name, content)
        return self.create_record(rtype, name, content)

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self.list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids.append(identifier)
        LOGGER.debug("Record IDs to delete: %s", delete_record_ids)
        for rec_id in delete_record_ids:
            # POST to the DNS management UI with form values to delete the record
            delete_response = self.session.post(
                "https://dns.he.net/index.cgi",
                data={
                    "menu": "edit_zone",
                    "hosted_dns_zoneid": self.domain_id,
                    "hosted_dns_recordid": rec_id,
                    "hosted_dns_editzone": "1",
                    "hosted_dns_delrecord": "1",
                    "hosted_dns_delconfirm": "delete",
                },
            )

            # Parse the HTML response, if the <div> tag indicating success isn't found, error
            html = BeautifulSoup(delete_response.content, "html.parser")
            if html.find("div", {"id": "dns_status"}) is None:
                LOGGER.warning("Unable to delete record %s", rec_id)
                return False
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # Helper _request is not used in this provider
        pass
