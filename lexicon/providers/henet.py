from __future__ import absolute_import
from __future__ import print_function
import re, logging
from sys import stderr
from os import environ
from time import sleep
from requests import Session
# Due to optional requirement
try:
    from bs4 import BeautifulSoup
except ImportError:
   pass

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

def ProviderParser(subparser):
    subparser.description = """A provider for Hurricane Electric DNS.
        NOTE: THIS DOES NOT WORK WITH 2-FACTOR AUTHENTICATION.
              YOU MUST DISABLE IT IF YOU'D LIKE TO USE THIS PROVIDER.
        """
    subparser.add_argument(
        '--auth-username',
        help='Specify username used to authenticate'
    )
    subparser.add_argument(
        '--auth-password',
        help='Specify password used to authenticate',
    )


class Provider(BaseProvider):
    """
        he.net provider
    """

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.options = options
        self.domain = self.options['domain']
        self.domain_id = None

    def authenticate(self):
        """
        """
        # Create the session GET the login page to retrieve a session cookie
        self.session = Session()    
        self.session.get(
            "https://dns.he.net/"
        )

        # Hit the login page with authentication info to login the session
        login_response = self.session.post(
           "https://dns.he.net",
            data={
                "email": self.options.get('auth_username',''),
                "pass": self.options.get('auth_password','')
            }
        )

        # Parse in the HTML, if the div containing the error message is found, error
        html = BeautifulSoup(login_response.content, "html.parser")
        if html.find("div", {"id": "dns_err"}) is not None:
            logger.warning("HE login failed, check HE_USER and HE_PASS")
            return False

        # Make an authenticated GET to the DNS management page
        zones_response = self.session.get(
            "https://dns.he.net"
        )

        html = BeautifulSoup(zones_response.content, "html.parser")
        zone_img = html.find("img", {"name": self.options.get("domain",''), "alt": "delete"})

        # If the tag couldn't be found, error, otherwise, return the value of the tag
        if zone_img is None:
            logger.warning("Domain {0} not found in account".format(self.options.get("domain",'')))
            raise AssertionError("Domain {0} not found in account".format(self.options.get("domain",'')))

        self.domain_id = zone_img["value"]
        logger.debug("HENET domain ID: {}".format(self.domain_id))
        return True

    # Create record. If record already exists with the same content, do nothing
    def create_record(self, type, name, content):
        logger.debug("Creating record for zone {0}".format(name))
        # Pull a list of records and check for ours
        records = self.list_records(type=type, name=name, content=content)
        if len(records) >= 1:
            logger.warning("Duplicate record {} {} {}, NOOP".format(type, name, content))
            return True
        data={
            "account": "",
            "menu": "edit_zone",
            "Type": type,
            "hosted_dns_zoneid": self.domain_id,
            "hosted_dns_recordid": "",
            "hosted_dns_editzone": "1",
            "Priority": "",
            "Name": name,
            "Content": content,
            "TTL": "3600",
            "hosted_dns_editrecord": "Submit"
        }
        ttl = self.options.get('ttl')
        if ttl:
            if ttl <= 0: 
                data['TTL'] = "3600"
            else:
                data['TTL'] = str(ttl)
        prio = self.options.get('priority')
        if prio:
            if prio <= 0: 
                data['Priority'] = "10"
            else:
                data['Priority'] = str(prio)
        create_response = self.session.post(
            "https://dns.he.net/index.cgi", data=data
        )
        # Pull a list of records and check for ours
        records = self.list_records(name=name)
        if len(records) >= 1:
            logger.info("Successfully added record {}".format(name))
            return True
        else:
            logger.info("Failed to add record {}".format(name))
            return False

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is
    # received.
    def list_records(self, type=None, name=None, content=None, id=None):
        records = []
        # Make an authenticated GET to the DNS management page
        edit_response = self.session.get(
            "https://dns.he.net/?hosted_dns_zoneid={0}&menu=edit_zone&hosted_dns_editzone".format(self.domain_id)
        )

        # Parse the HTML response, and list the table rows for DNS records
        html = BeautifulSoup(edit_response.content, "html.parser")
        def is_dns_tr_type(klass):
            return klass and re.compile("dns_tr").search(klass)
        records = html.findAll("tr", class_=is_dns_tr_type)

        # If the tag couldn't be found, error, otherwise, return the value of the tag
        if records is None or len(records) == 0:
            logger.warning("Domains not found in account")
        else:
            new_records = []
            for dns_tr in records:
                tds = dns_tr.findAll("td")
                # Process HTML in the TR children to derive each object
                rec = {}
                rec['zone_id'] = tds[0].string
                rec['id'] = tds[1].string
                rec['name'] = tds[2].string
                # the 4th entry is a comment
                type_elem = tds[3].find("span", class_='rrlabel')
                if type_elem:
                    rec['type'] = type_elem.string
                else:
                    rec['type'] = None
                rec['ttl'] = tds[4].string
                if tds[5].string != '-':
                    rec['priority'] = tds[5]
                rec['content'] = tds[6].string
                if tds[7].string == '1':
                    rec['is_dynamic'] = True
                else:
                    rec['is_dynamic'] = False
                rec = self._clean_TXT_record(rec)
                new_records.append(rec)
            records = new_records
            if id:
                logger.debug("Filtering {} records by id: {}".format(len(records), id))
                records = [record for record in records if record['id'] == id]
            if type:
                logger.debug("Filtering {} records by type: {}".format(len(records), type))
                records = [record for record in records if record['type'] == type]
            if name:
                logger.debug("Filtering {} records by name: {}".format(len(records), name))
                if name.endswith('.'):
                    name = name[:-1]
                records = [record for record in records if name in record['name'] ]
            if content:
                logger.debug("Filtering {} records by content: {}".format(len(records), content.lower()))
                records = [record for record in records if record['content'].lower() == content.lower()]
            logger.debug("Final records ({}): {}".format(len(records), records))
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        # Delete record if it exists
        self.delete_record(identifier, type, name, content)
        return self.create_record(type, name, content)

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        delete_record_ids = []
        if not identifier:
            records = self.list_records(type, name, content)
            delete_record_ids = [record['id'] for record in records]
        else:
            delete_record_ids.append(identifier)
        logger.debug("Record IDs to delete: {}".format(delete_record_ids))
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
                    "hosted_dns_delconfirm": "delete"
                }
            )

            # Parse the HTML response, if the <div> tag indicating success isn't found, error
            html = BeautifulSoup(delete_response.content, "html.parser")
            if html.find("div", {"id": "dns_status"}) is None:
                logger.warning("Unable to delete record {}".format(rec_id))
                return False
        return True
