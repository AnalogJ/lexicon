"""Module provider for Mythic Beasts"""
from __future__ import absolute_import

import json
import logging

import requests
import hashlib
from lexicon.providers.base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ["mythic-beasts.com"]


def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.description = """
        There are two ways to provide an authentication granting access to the Mythic Beasts API
        1 - With your API credentials (user/password),
            with --auth-username and --auth-password flags.
        2 - With an API token, using --auth-token flags.
        These credentials and tokens must be generated using the Mythic Beasts API v2.
    """
    subparser.add_argument(
        "--auth-username",
        help="specify API credentials username",
    )
    subparser.add_argument(
        "--auth-password",
        help="specify API credentials password",
    )
    subparser.add_argument(
        "--auth-token",
        help="specify API token for authentication",
    )
   


class Provider(BaseProvider):
    """Provider class for Cloudflare"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = "https://api.mythic-beasts.com/dns/v2"
        self.auth_token = None

    def _authenticate(self):
        
        #import pdb;pdb.set_trace()
        
        payload = self._get("/zones")

        if self.domain is None:
            if not payload["zones"]:
                raise Exception("No domain found")
            if len(payload["zones"])>1:
                raise Exception("Too many domains found. This should not happen")    
            else:
                self.domain = payload["zones"][0]
        else:
            if not payload["zones"]:
                raise Exception("No domain found")
            if self.domain not in payload["zones"]:
                raise Exception("Requested domain not found")

        self.domain_id = hashlib.md5(self.domain.encode('utf-8')).hexdigest()

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        # content, cf_data = self._format_content(rtype, content)
        LOGGER.debug("type %s",rtype)
        LOGGER.debug("name %s",name)
        LOGGER.debug("content %s",content)
        
        # duplicate = None

        data = {
            "records": [{
                "host": self._full_name(name),
                "type": rtype,
                "data": content,
            }]
        }
        if self._get_lexicon_option("ttl"):
            data["records"][0]["ttl"] = self._get_lexicon_option("ttl")

        payload = {"success": True}
        try:
            payload = self._post(f"/zones/{self.domain}/records", data)
        except requests.exceptions.HTTPError as err:
            if err.response.status_code != 400:
                raise
            # else:
            #     duplicate = 1

        # if name == "_acme-challenge.deleterecordinset.lexitus.co.uk.":
        #     import pdb;pdb.set_trace()


        if "message" in payload:
            return payload["message"]
        elif "success" in payload:
            return payload["success"]

        #LOGGER.debug("create_record: %s", payload["message"])
        # try:
        #     return payload["message"]
        # except:
        #     i
        #     import pdb;pdb.set_trace()

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        filter_obj = {}
        if rtype:
            filter_obj["type"] = rtype
        if name:
            filter_obj["host"] = self._full_name(name)
        if content:
            filter_obj["data"] = content
        
        records = []
        
        payload = self._get(f"/zones/{self.domain}/records", filter_obj)

        LOGGER.debug("payload: %s", payload)

        for record in payload["records"]:
            processed_record = {
                "type": record["type"],
                "name": record["host"],
                "ttl": record["ttl"],
                "content": record["data"],
                "id":  hashlib.md5((record["host"] + record["type"] + record["data"]).encode('utf-8')).hexdigest()
            }
            if(record["type"]=='MX' and record["mx_priority"]):
                processed_record["options"]= {"mx": {"priority": record["mx_priority"]}}

            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        LOGGER.debug("Number of records retrieved: %d", len(records))
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):

        
        if identifier is None:
            import pdb;pdb.set_trace()
            records = self._list_records(rtype,name,content)
            if len(records) == 1:
                matching_record = records[0]
                filter_obj = {}
                filter_obj["type"] = matching_record["type"]
                filter_obj["host"] = matching_record["name"]

            elif len(records) < 1:
                raise Exception(
                    "No records found matching type and name - won't update"
                )
            else:
                raise Exception(
                    "Multiple records found matching type and name - won't update"
                )
        else:
            records = self._list_records()
            for record in records:
                if record['id'] == identifier:
                    matching_record = record
                    break
            else:
                raise Exception("Can't find record with that id!")

            filter_obj = {}
            filter_obj["type"] = matching_record["type"]
            filter_obj["host"] = matching_record["name"]
            filter_obj["data"] = matching_record["content"]   

        data = {"records":[{}]}
        if rtype:
            data["type"] = rtype
        if name:
            data["host"] = self._full_name(name)
        if content:
            data["records"][0]["data"] = content
        if self._get_lexicon_option("ttl"):
            data["records"][0]["ttl"] = self._get_lexicon_option("ttl")

        LOGGER.debug(data)
        
        payload = self._put(f"/zones/{self.domain}/records/{matching_record['name']}/{matching_record['type']}", data, filter_obj)

        LOGGER.debug("update_record: %s", payload["message"])
        return payload["message"]

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        filter_obj = {}
        if rtype:
            filter_obj["type"] = rtype
        if name:
            filter_obj["host"] = self._full_name(name)
        if content:
            filter_obj["data"] = content
        
        records = self._list_records(rtype, name, content)



        # if name == "_acme-challenge.deleterecordinset.lexitus.co.uk.":
        #     import pdb;pdb.set_trace()

        for record in records:
            LOGGER.debug("delete_records: %s", record)
            name = record["name"]
            rtype = record["type"]
            if identifier is not None and identifier!=record["id"]:
                continue
            
            
            self._delete(f"/zones/{self.domain}/records/{name}/{rtype}",filter_obj)

        LOGGER.debug("delete_record: %s", True)
        return True

    # Helpers
    def _request(self, action="GET", url="/", data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        

        # may need to get auth token
        if self.auth_token is None and self._get_provider_option('auth_token') is None:
            auth_request = requests.request(
             "POST",
             "https://auth.mythic-beasts.com/login",
             data={
                 "grant_type": "client_credentials"
             },
             auth=(self._get_provider_option("auth_username"),self._get_provider_option("auth_password"))
            )

            auth_request.raise_for_status()
            post_result = auth_request.json()

            if not post_result["access_token"]:
                raise Exception(
                    "Error, could not get access token "
                    f"for Mythic Beasts API for user: {self._get_provider_option('auth_username')}"
                )

            self.auth_token = post_result["access_token"]
        elif self.auth_token is None:
            self.auth_token = self._get_provider_option('auth_token')

        headers = {"Content-Type": "application/json"}
        headers["Authorization"] = f"Bearer {self.auth_token}"
        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    def _format_content(self, rtype, content):
        """
        Special case handling from some record types that Cloudflare needs
        formatted differently

        Returns new values for the content and data properties to be sent
        on the request
        """
        data = None
        if rtype == "SSHFP":
            # For some reason the CloudFlare API does not let you set content
            # directly when creating an SSHFP record. You need to pass the
            # fields that make up the record seperately, then the API joins
            # them back together
            _fp = content.split(" ")
            data = {"algorithm": _fp[0], "type": _fp[1], "fingerprint": _fp[2]}
            content = None

        return content, data
