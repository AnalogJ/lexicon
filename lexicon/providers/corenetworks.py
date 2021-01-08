"""Module provider for Core Networks"""
from __future__ import absolute_import
import json
import hashlib
import logging
import time
import os
import tempfile

import requests
from lexicon.providers.base import Provider as BaseProvider

CorenetworksLog = logging.getLogger(__name__)
#CorenetworksLog.setLevel(logging.DEBUG)

NAMESERVER_DOMAINS = ['core-networks.de', 'core-networks.eu', 'core-networks.com']

def provider_parser(subparser):
    """Configure provider parser for Core Networks"""
    subparser.add_argument(
        "--auth-username", help="Specify login for authentication")
    subparser.add_argument(
        "--auth-password", help="Specify password for authentication")
    subparser.add_argument(
        "--auth-file", help="Specify location for authentication file. If this contains a valid token it will be used. Otherwise --auth-username and --auth-password are necessary. Defaults to ~/corenetworks_auth.json if ~ is writable by lexicon, otherwise $TMP/corenetworks_auth.json. In most cases you don't need to specify it as it will be used by default before acquiring a new token from the provider. The token has a lifetime of 1 hour after which it must be re-issued using the credentials. The most common use-case would be to consistently set this to some secure location where only lexicon has access. Might be deprecated in the future.")

class Provider(BaseProvider):
    """Provider class for Core Networks"""
    def __init__(self, config):
        CorenetworksLog.info("Initialising class Provider")
        super(Provider, self).__init__(config)
        self.domain_id = None       # zone name
        self.account_id = None      # unused?
        self.token = None           # provided by service after auth
        self.expiry = None          # token expiry time, calculated after auth
        self.modified = False       # some API calls need to be committed; this will be done on object destruction in __del__
        self.auth_file = { 'token': None, 'expiry': None }
        # Core Networks enforces a limit on the amount of logins per minute.
        # As the token is valid for 1 hour it's sensible to store it for
        # later usage.
        if os.path.exists(os.path.expanduser("~"))  and os.path.expanduser("~") != '':
            path = os.path.expanduser("~")
        else:
            path = tempfile.gettempdir()
        self.auth_file_path = self._get_provider_option('auth_file') or (path+'/corenetworks_auth.json')
        self.api_endpoint = 'https://beta.api.core-networks.de'

    def __del__(self):
        """Destructor of the class.
        Changes to the zone need to be committed.
        # https://beta.api.core-networks.de/doc/#functon_dnszones_commit"""
        if self.modified == True:
            payload = self._post("/dnszones/{0}/records/commit".format(self.domain))
            self.modified == False
        return True

    def _authenticate(self):
        """Authenticate by either providing stored access token or
        acquiring and storing token. This method will query the
        list of zones and store them for later use. If the requested
        domain is not in the list of zones it will raise an exception.
        Ref: https://beta.api.core-networks.de/doc/#functon_auth_token"""
        CorenetworksLog.debug("Entering _authenticate, requesting domain %s" % self.domain)
        self._retrieve_auth_file()
        CorenetworksLog.info("Value of self.auth_file: %s" % self.auth_file)
        if 'token' in self.auth_file:
            self.token = self.auth_file['token']
            self.expiry = self.auth_file['expiry']

            # Fetch new auth token if expiry is less than 60 seconds away
            # as it can be we have to wait up to 60 seconds because of
            # provider rate limiting.
            if self.expiry-time.time() < 60:
                self._get_token()
        else:
            self._get_token()

        CorenetworksLog.info("self.expiry is %s" % self.expiry)
        # Store zones for saving one API call
        self.zones = self._list_zones()

        #Check if requested zone is in zones list
        zone = next((zone for zone in self.zones if zone["name"] == self.domain), None)
        if not zone:
            raise Exception('No domain found like %s.' % self.domain)
        else:
            self.domain_id = zone['name']
        return True


    def _list_records(self, rtype=None, name=None, content=None):
        """List all records. Return an empty list if no records found
        type, name and content are used to filter records.
        If possible filter during the query, otherwise filter after response is received.
        Ref: https://beta.api.core-networks.de/doc/#functon_dnszones_records"""
        CorenetworksLog.debug("Entering _list_records")
        zone = next((zone for zone in self.zones if zone["name"] == self.domain), None)
        if not zone:
            raise Exception('Domain not found')
        query_params = {}
        if rtype:
            query_params['type'] = rtype
        if name:
            query_params['name'] = self._relative_name(name)
        if content:
            query_params['data'] = content
        payload = self._get("/dnszones/{0}/records/".format(self.domain), query_params)
        for record in payload:
            record['content'] = record.pop('data')
            record['name'] = self._full_name(record['name'])
            # Core Networks' API does not provide unique IDs for each record
            # so we generate them ourselves.
            record['id'] = self._make_identifier( rtype = record['type'], name = record['name'], content = record['content'] )
        return payload

    def _create_record(self, rtype, name, content):
        """Creates a record. If record already exists with the same content, do nothing."""
        CorenetworksLog.debug("Entering _create_record")

        # Check for existence of record.
        existing_records = self._list_records(rtype, name, content)
        new_record_id = self._make_identifier(rtype, self._full_name(name), content)
        record = next((r for r in existing_records if r["id"] == new_record_id), None)
        # Nothing to do if true.
        if record:
            return True

        data = {
            'name': self._relative_name(name),
            'data': content,
            'type': rtype
        }
        if self._get_lexicon_option('ttl'):
            data['ttl'] = self._get_lexicon_option('ttl')
            # Bug reported by chkpnt. If ttl is less than 60s the API throws a "415 Client Error: Unsupported Media Type"
            if data['ttl'] < 60:
                data['ttl'] = 60
        if self._get_lexicon_option('priority'):
            data['priority'] = self._get_lexicon_option('priority')

        payload = self._post("/dnszones/{0}/records/".format(self.domain), data)
        # Changes to the zone need to be committed.
        # https://beta.api.core-networks.de/doc/#functon_dnszones_commit
        self.modified = True

        return new_record_id

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        """Updates a record. Core Networks neither supports updating a record nor is able to reliably identify a record
        after a change. The best we can do is to identify the record by ourselves, fetch its data, delete it and
        re-create it."""
        CorenetworksLog.debug("Entering _update_record")
        if identifier is not None:
            # Check for existence of record
            existing_records = self._list_records(rtype)
            record = next((r for r in existing_records if r["id"] == identifier), None)
            if not record:
                return True
            if rtype:
                record['type'] = rtype
            if name:
                record['name'] = self._relative_name(name)
            if content:
                record['content'] = content
            if self._delete_record(identifier):
                new_id = self._create_record(rtype = record['type'], name = record['name'], content = record['content'])
                return new_id
        else:
            records = self._list_records( rtype=rtype, name=self._relative_name(name) )
            if len(records) > 0:
                if len(records) > 1:
                    CorenetworksLog.warning("Found %s records, will only update the first record in search result list." % len(records))
                record = records[0]
                return self._update_record( record['id'], rtype, name, content )
            else:
                return True
        return False

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """Delete an existing record.
        If record does not exist, do nothing.
        Ref: https://beta.api.core-networks.de/doc/#functon_dnszones_records_delete"""
        CorenetworksLog.debug("Entering _delete_record")
        if identifier is not None:
            # Check for existence of record
            existing_records = self._list_records( rtype, name, content )
            record = next((r for r in existing_records if r["id"] == identifier), None)
            if not record:
                return True
            data = {
                'name': self._relative_name(record['name']),
                'data': record['content'],
                'type': record['type']
            }
            payload = self._post("/dnszones/{0}/records/delete".format(self.domain), data)
            # Changes to the zone need to be committed.
            # https://beta.api.core-networks.de/doc/#functon_dnszones_commit
            self.modified = True
        else:
            records = self._list_records( rtype, name, content)
            if len(records) > 0:
                for record in records:
                    self._delete_record(identifier = record['id'], rtype = record['type'], name = record['name'], content = record['content'] )
                # Changes to the zone need to be committed.
                # https://beta.api.core-networks.de/doc/#functon_dnszones_commit
                self.modified = True
            else:
                return True
        return True

    # Helpers

    def _request(self, action='GET', url='/', data=None, query_params=None):
        CorenetworksLog.debug("Entering _request")
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        CorenetworksLog.info( "url: %s with data %s and query_params %s" % ( url, str(data), str(query_params) ) )
        default_headers = {}

        if self.token:
            default_headers['Authorization'] = "Bearer {0}".format(self.token)

        response = requests.request(action,
            self.api_endpoint + url,
            params=query_params,
            data=json.dumps(data),
            headers=default_headers,
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        if response.text and response.json() is None:
            raise Exception('No data returned')

        return response.json() if response.text else None

    def _list_zones(self):
        """List existing zones.
        Ref: https://beta.api.core-networks.de/doc/#functon_dnszones"""
        CorenetworksLog.debug("Entering _list_zones")
        return self._get('/dnszones/')

    def _make_identifier(self, rtype, name, content):
        return hashlib.sha1('/'.join([ rtype, name, content ]).encode('utf-8')).hexdigest()

    def _retrieve_auth_file(self):
        """Retrieve token and zones from json file"""
        # I guess the correct way would be multiple nested checks for
        # existence of path, checking if path is a file, checking if
        # file is readable and so on, and each one with corresponding
        # exceptions.
        if(os.path.exists(self.auth_file_path) and os.path.isfile(self.auth_file_path)):
            try:
                auth = open(self.auth_file_path, "r")
                if auth.mode == "r":
                    self.auth_file = json.loads(auth.read())
                    auth.close()
                    return True
                else:
                    auth.close()
                    return False
            except FileNotFoundError as e:
                CorenetworksLog.info("No stored authentication found: %s. Acquiring token via API call." % os.strerror(e.errno))
                self._get_token()
                return True
        else:
            self._get_token()
            return True

    def _commit_auth_file(self):
        """Store authentication into json file."""
        try:
            auth = open(self.auth_file_path, "w")
            if auth.mode == "w":
                content = json.dumps(self.auth_file)
                auth.write(content)
                os.chmod(self.auth_file_path, 0o600)
                return True
            else:
                return False
        except IOError as e:
            CorenetworksLog.warning("Could not write authentication file: %s" % os.strerror(e.errno))
        finally:
            auth.close()

    def _get_token(self):
        """Request new token via API call"""
        CorenetworksLog.debug("Entering _get_token.")
        if self._get_provider_option('auth_username') == None or self._get_provider_option('auth_password') == None:
            raise Exception("No valid authentication mechanism found")
        else:
            data = {
                'login'   : self._get_provider_option('auth_username'),
                'password': self._get_provider_option('auth_password')
            }
            payload = self._post('/auth/token', data = data)
            self.token  = payload['token']
            self.expiry = payload['expires'] + time.time()

            # Prepare auth file and commit changes
            self.auth_file['token']  = self.token
            self.auth_file['expiry'] = self.expiry
            self._commit_auth_file()

