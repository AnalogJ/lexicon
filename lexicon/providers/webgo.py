"""Module provider for Webgo"""
import logging


from bs4 import BeautifulSoup  # type: ignore
from requests import Session

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["webgo.de"]


def provider_parser(subparser):
    """Configure provider parser for Webgo."""
    subparser.description = """A provider for Webgo."""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )


class Provider(BaseProvider):
    """
    webgo.de provider
    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain = self.domain
        self.domain_id = None
        self.session = None

    def _authenticate(self):
        # Create the session GET the login page to retrieve a session cookie
        self.session = Session()
        self.session.get("https://login.webgo.de/")

        # Hit the login page with authentication info to login the session
        login_response = self.session.post(
            "https://login.webgo.de/login",
            data={
                "data[User][username]": self._get_provider_option("auth_username") or "",
                "data[User][password]": self._get_provider_option("auth_password") or "",
            },
        )

        # Parse in the HTML, if the div containing the error message is found, error
        html = BeautifulSoup(login_response.content, "html.parser")
        if html.find("div", {"class": "loginformerror"}) is not None:
            LOGGER.warning("Webgo login failed, check Username and Password")
            raise AuthenticationError("Webgo login failed, check Username and Password")
            return False

        # Make an authenticated GET to the DNS management page
        zones_response = self.session.get("https://login.webgo.de/domains")

        html = BeautifulSoup(zones_response.content, "html.parser")
        domain_table = html.find("table", {"class": "alltable"})
        rows = domain_table.find_all('tr')
        dns_link = None
        for row in rows[1:]:
            domain = row.findAll('td')[1].renderContents().decode()
            if domain == self.domain:
                dns_link = row.findAll('td')[5]
                dns_link = dns_link.find("a", {"class": "domainButton fcon-sliders"}).get('href')

        # If the Domain couldn't be found, error, otherwise, return the value of the tag
        if dns_link is None:
            LOGGER.warning("Domain %s not found in account", self.domain)
            raise AuthenticationError(f"Domain {self.domain} not found in account")

        self.domain_id = dns_link.rsplit("/", 1)[1]
        LOGGER.debug("Webgo domain ID: %s", self.domain_id)
        return True

    # Create record. If record already exists with the same content, do nothing
    def _create_record(self, rtype, name, content):
        LOGGER.debug("Creating record for zone %s", name)
        # Pull a list of records and check for ours
        if rtype == "CNAME" and not content.endswith("."):
            content += "."
        records = self._list_records(rtype=rtype, name=name, content=content)
        LOGGER.info(records)
        if len(records) >= 1:
            LOGGER.warning("Duplicate record %s %s %s, NOOP", rtype, name, content)
            return True
        data = {
            "data[DnsSetting][sub]": name,
            "data[DnsSetting][ttl]": "3600",
            "data[DnsSetting][rr-typ]": rtype,
            "data[DnsSetting][pref-mx]": "0",
            "data[DnsSetting][value]": content,
            "data[DnsSetting][action]": "newsub",
            "data[DnsSetting][domain_id]": self.domain_id,
               }
        ttl = self._get_lexicon_option("ttl")
        if ttl:
            if ttl <= 0:
                data["data[DnsSetting][ttl]"] = "3600"
            else:
                data["data[DnsSetting][ttl]"] = str(ttl)
        prio = self._get_lexicon_option("priority")
        if prio:
            if prio <= 0:
                data["data[DnsSetting][pref-mx]"] = "10"
            else:
                data["data[DnsSetting][pref-mx]"] = str(prio)

        self.session.post("https://login.webgo.de/dns_settings/domainDnsEditForm", data=data)
        self.session.get(f"https://login.webgo.de/dnsSettings/domainDnsDo/{self.domain_id}/ok")
        # Pull a list of records and check for ours
        records = self._list_records(name=name)
        if len(records) >= 1:
            LOGGER.info("Successfully added record %s", name)
            return True
        LOGGER.info("Failed to add record %s", name)
        return False

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is
    # received.
    def _list_records(self, rtype=None, name=None, content=None):
        return self._list_records_internal(rtype=rtype, name=name, content=content)

    def _list_records_internal(
        self, rtype=None, name=None, content=None, identifier=None
    ):
        records = []
        # Make an authenticated GET to the DNS management page
        edit_response = self.session.get(
            f"https://login.webgo.de/dnsSettings/domainDnsEdit/{self.domain_id}",
        )

        # Parse the HTML response, and list the table rows for DNS records
        html = BeautifulSoup(edit_response.content, "html.parser")
        dns_table = html.find("table", {"class": "alltable"})
        records = dns_table.findAll("tr")

        # If the tag couldn't be found, error, otherwise, return the value of the tag
        if records is None or not records:
            LOGGER.warning("Domains not found in account")
            return records

        new_records = []
        for dns_tr in records[1:]:
            tds = dns_tr.findAll("td")
            # Process HTML in the TR children to derive each object
            rec = {}
            rec["name"] = self._full_name(tds[0].string)
            rec["ttl"] = tds[1].string
            rec["type"] = tds[2].string
            rec["prio"] = tds[3].string
            rec["content"] = tds[4].string
            dns_link = tds[5]
            dns_link = dns_link.find("a", {"class": "domainButton fcon-edit"}).get('href')
            rec["id"] = dns_link.rsplit("/", 2)[1]
            if rec["content"].startswith('"'):
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
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # Delete record if it exists
        self._delete_record(identifier, rtype, name, content)
        return self._create_record(rtype, name, content)

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_ids = [record["id"] for record in records]
        else:
            delete_record_ids.append(identifier)
        LOGGER.debug("Record IDs to delete: %s", delete_record_ids)
        for rec_id in delete_record_ids:
            response = self.session.get(f"https://login.webgo.de/dnsSettings/domainDnsDo/{rec_id}/delete")
            if response.status_code == 200:
                self.session.get(f"https://login.webgo.de/dnsSettings/domainDnsDo/{self.domain_id}/ok")
            else:
                LOGGER.warning("Unable to delete record %s", rec_id)
                return False
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # Helper _request is not used in this provider
        pass
