"""Module provider for Flexible Engine Cloud"""
import json
import logging

import requests
from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)
NAMESERVER_DOMAINS = ["flexibleengine.com"]

def provider_parser(subparser):
    """Configure provider parser for Flexible Engine Cloud"""
    subparser.add_argument("--auth-token", help="specify token for authentication")
    subparser.add_argument(
        "--zone-id",
        help="specify the zone id",
    )

class Provider(BaseProvider):
    """Provider class for Flexible Engine Cloud"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.api_endpoint = "https://dns.prod-cloud-ocb.orange-business.com/v2"
        self.domain_id = None

        # Handling missing required parameters
        if not self._get_provider_option("token"):
            raise Exception("Error, Token is not defined")

    def _authenticate(self):
        zone_id = self._get_provider_option("zone_id")

        if not zone_id:
            payload = self._get("/zones", {"name": self.domain})

            if not payload["zones"]:
                raise AuthenticationError("No domain found")
            if len(payload["zones"]) > 1:
                raise AuthenticationError(
                    "Too many domains found. This should not happen"
                )
            self.domain_id = payload["zones"][0]["id"]
        else:
            payload = self._get(f"/zones/{zone_id}/recordsets")
            self.domain_id = zone_id


    def _create_record(self, rtype, name, content):
        ttl = self._get_lexicon_option("ttl")

        # put string in array
        tmp=content
        content=[]
        content.append(tmp)

        # check if record already exists
        if not self._list_records(rtype, name, content):
            record = {
                "type": rtype,
                "name": name,
                "records": content,
                "ttl": ttl,
            }
            
            if rtype == "TXT":
                # Convert "String" to "\"STRING\"" 
                tmp = []
                tmp.append( '\"'+record["records"][0]+'\"' )
                record["records"] = tmp

            self._post(f"/zones/{self.domain_id}/recordsets", record)
            LOGGER.debug("create_record: %s", True)
            return True
        else:
            LOGGER.debug("create_record: %s", False)
            LOGGER.debug("record already exist.")
            return False

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        url = f"/zones/{self.domain_id}/recordsets"
        records = []
        payload = {}

        # Convert it to Array if it is not converted yet.
        if isinstance(content, str):
            tmp=content
            content=[]
            content.append(tmp)

        # Iterating recordsets
        next_url = url
        while next_url is not None:
            payload = self._get(next_url)
            if (
                "links" in payload
                and "next" in payload["links"]
            ):
                next_url = payload["links"]["next"]
            else:
                next_url = None

            for record in payload["recordsets"]:
                processed_record = {
                    "type": record["type"],
                    "name": record["name"],
                    "ttl": record["ttl"],
                    "content": record["records"],
                    "id": record["id"],
                }
                records.append(processed_record)

        if rtype:
            records = [record for record in records if record["type"] == rtype]

        if name:
            records = [
                record for record in records if record["name"].rstrip('.') == name.rstrip('.')
            ]

        if content:
            if len(content)>1:
                records = [
                    record
                    for record in records
                    if record["content"] == content
                ]

        LOGGER.debug("list_records: %s", records)
        return records

    # update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        data = {}

        if name:
            data["name"] = name

        if rtype:
            data["type"] = rtype

        ttl = self._get_lexicon_option("ttl")
        if ttl:
            data["ttl"] = ttl

        if content:
            if rtype == "TXT":
                content = '\"'+content+'\"'
            tmp=content
            content=[]
            content.append(tmp)
            data["records"] = content

        self._put(f"/zones/{self.domain_id}/recordsets/{identifier}", data)
        LOGGER.debug("update_record: %s", True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        
        tmp=content
        content=[]
        content.append(tmp)

        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record["id"] for record in records]
        else:
            delete_record_id.append(identifier)

        if delete_record_id:
            LOGGER.debug("delete_records: %s", delete_record_id)

            for record_id in delete_record_id:
                self._delete(f"/zones/{self.domain_id}/recordsets/{record_id}")

            # Is always True at this point, if a non 200 response is returned an error is raised.
            LOGGER.debug("delete_record: %s", True)
            return True
        else:
            LOGGER.debug("delete_record: %s", False)
            LOGGER.debug("No found record to delete.")
            return False

    # API requests
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Auth-Token": f"{self._get_provider_option('auth_token')}",
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