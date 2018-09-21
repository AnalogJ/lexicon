import logging

import requests
from collections import OrderedDict

try:
    import xmltodict # optional dependency
except ImportError:
    pass

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)

# Lexicon Plesk Provider
#
# Author: Jens Reimann, 2018
#
# API Docs: https://docs.plesk.com/en-US/onyx/api-rpc
#

plesk_url_suffix = "/enterprise/control/agent.php"

def ProviderParser(subparser):
    subparser.add_argument("--auth-username", help="specify user used authenticate")
    subparser.add_argument("--auth-password", help="specify password used authenticate")
    subparser.add_argument('--plesk-server', help="specify URL to the Plesk Web UI, including the port")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)

        self.api_endpoint = self.options.get('plesk_server')

        if self.api_endpoint.endswith('/'):
            self.api_endpoint = self.api_endpoint[:-1]

        if not self.api_endpoint.endswith(plesk_url_suffix):
            self.api_endpoint += plesk_url_suffix

        self.site_name = self.options.get('domain')
        assert self.site_name is not None

        self.domain_id = None

        self.username = self.options.get('auth_username')
        assert self.username is not None

        self.password = self.options.get('auth_password')
        assert self.password is not None

    def __simple_request(self, type, operation, req):
        
        response = self.__plesk_request({
            type: {
                operation: req
            }
        })[type][operation]
        
        result = response["result"]
        
        if isinstance(result, list):
            for r in result:
                if r["status"] == "error":
                    raise Exception("API returned at least one error: %s" % r["errtext"] )
        elif response["result"]["status"] == "error":
            errcode = response["result"]["errcode"]
            errtext = response["result"]["errtext"]
            raise Exception("API returned error: %s (%s)" % ( errcode, errtext ) )
        
        return response

    def __plesk_request(self, request):

        headers = {}
        headers["Content-type"] = "text/xml"
        headers["HTTP_PRETTY_PRINT"] = "TRUE"
        headers["HTTP_AUTH_LOGIN"] = self.username
        headers["HTTP_AUTH_PASSWD"] = self.password

        xml = xmltodict.unparse({
                "packet": request
            }, pretty=True)

        logger.debug ( "Request: %s", xml)

        r = requests.post(self.api_endpoint, headers=headers, data=xml,  auth=(self.username, self.password))

        data = r.text

        logger.debug ( "Response: %s", data )
        result = xmltodict.parse(data )
        return result["packet"]

    def __find_site(self):
        return self.__simple_request('site', 'get', OrderedDict([
            ('filter', {'name': self.site_name}),
            ('dataset', {})
        ]))["result"]["id"]

    def authenticate(self):
        self.domain_id = self.__find_site()
        
        if self.domain_id == None:
            raise Exception('Domain not found')

    def create_record(self, type, name, content):
        return self.__create_entry(type, name, content, None)

    def list_records(self, type=None, name=None, content=None):
        entries = self.__find_dns_entries(type, name, content)
        logger.debug("list_records: %s" % entries)
        return entries

    def update_record(self, identifier, type=None, name=None, content=None):
        
        if identifier is None:
            entries = self.__find_dns_entries(type, name, None)
            logger.debug("Entries found: %s", entries)
            
            if len(entries) < 1:
                raise Exception("No entry found for updating")
            
            identifier = entries[0]["id"]
            entry = self.__get_dns_entry(identifier)
            
            ids = []
            for e in entries:
                ids.append(e["id"])
            
            self.__delete_dns_records_by_id(ids)
            
        else:
            
            entry = self.__get_dns_entry(identifier)
            self.__delete_dns_records_by_id([identifier])

        assert entry is not None

        logger.debug("Updating: %s", entry)

        if type:
            entry["type"] = type
        if name:
            entry["host"] = name
        if content:
            entry["value"] = content
        
        return self.__create_entry(entry["type"], entry["host"], entry["value"], entry["opt"])

    def __create_entry(self, type, host, value, opt):
        entries = self.__find_dns_entries(type, self._fqdn_name(host), value)
        
        if entries:
            return True # already exists

        self.__simple_request('dns','add_rec',OrderedDict([
            ('site-id', self.domain_id),
            ('type', type),
            ('host', self._relative_name(host)),
            ('value', value),
            ('opt', opt)
        ]))
        
        return True


    def delete_record(self, identifier=None, type=None, name=None, content=None):
        
        if identifier:
            
            self.__delete_dns_records_by_id([identifier])
            return True
            
        else:
            
            entries = self.__find_dns_entries ( type, self._fqdn_name(name), content )
            ids = []
            
            for entry in entries:
                ids.append(entry["id"])
            
            self.__delete_dns_records_by_id(ids)
            return len(ids) > 0

    def __get_dns_entry(self, id):
        return self.__simple_request('dns', 'get_rec', {
            'filter': {
                'id': id
            }
        })["result"]["data"]

    def __find_dns_entries(self, type = None, host = None, value = None):
        logger.debug("Searching for: %s, %s, %s", type, host, value )

        if value and type and type in ["CNAME"]:
            logger.debug("CNAME transformation")
            value = value.rstrip('.') + "."

        if host:
            host = self._fqdn_name(host)

        result = self.__simple_request('dns', 'get_rec', {
           'filter': {
                'site-id': self.domain_id
            }
        })

        entries = []

        for r in result["result"]:

            logger.debug("Record: %s", r)

            if ( type is not None ) and ( r["data"]["type"] != type ):
                logger.debug("\tType doesn't match - expected: '%s', found: '%s'", type, r["data"]["type"])
                continue
            
            if ( host is not None ) and ( r["data"]["host"] != host ):
                logger.debug("\tHost doesn't match - expected: '%s', found: '%s'", host, r["data"]["host"])
                continue
            
            if ( value is not None ) and ( r["data"]["value"] != value ):
                logger.debug("\tValue doesn't match - expected: '%s', found: '%s'", value, r["data"]["value"])
                continue

            entry = {
                'id': r["id"],
                'type': r["data"]["type"],
                'name': self._full_name(r["data"]["host"]),
                'ttl': None,
                'options': {}
            }
            
            if r["data"]["type"] in ("CNAME"):
                entry['content'] = r["data"]["value"].rstrip('.')
            else:
                entry['content'] = r["data"]["value"]

            if r["data"]["type"] == "MX":
                entry['options']['mx'] = {
                    'priority': int(r["data"]["opt"])
                }

            entries.append(entry)

        return entries

    def __delete_dns_records_by_id(self, ids):
        if not ids:
            return

        req = []
        for i in ids:
            req.append({
                'del_rec': {
                    'filter': {
                        'id': i
                    }
                }
            })

        self.__plesk_request({
            'dns': req
        })
