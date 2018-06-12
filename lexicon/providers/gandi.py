import json
import logging
import requests

from builtins import object
from .base import Provider as BaseProvider

try:
    import xmlrpclib
except ImportError:
    import xmlrpc.client as xmlrpclib

LOGGER = logging.getLogger(__name__)

def ProviderParser(subparser):
    """Specify arguments for Gandi Lexicon Provider."""
    subparser.add_argument('--auth-token', help="specify Gandi API key")
    subparser.add_argument('--auth-protocol', help="specify Gandi API protocol to use (RPC or REST, RPC by default if not specified)")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options)
        self.default_ttl = 3600
        self.protocol = self.options.get('auth_protocol', 'RPC')

        if (self.protocol != 'RPC' and self.protocol != 'REST'):
            raise ValueError("Invalid auth protocol specified, should be 'RPC' or 'REST'")

        if (self.protocol == 'RPC'):
            self.rpc_helper = GandiRPCSubProvider(self.options['auth_token'], 
                                                  self.options.get('api_endpoint', 'https://rpc.gandi.net/xmlrpc/'), 
                                                  self.options['domain'].lower(),
                                                  self._relative_name,
                                                  self._full_name)
        else:
            self.api_endpoint = self.options.get('api_endpoint', 'https://dns.api.gandi.net/api/v5')

    def authenticate(self):
        if (self.protocol == 'RPC'):
            domain_id = self.rpc_helper.authenticate()
            self.domain_id = domain_id
        else:
            self._get('/domains/{0}'.format(self.options['domain']))
            self.domain_id = self.options['domain'].lower()

    def create_record(self, type, name, content):
        if (self.protocol == 'RPC'):
            return self.rpc_helper.create_record(type, self._relative_name(name), 
                                                 content, self.options.get('ttl') or self.default_ttl)

        current_values = [record['content'] for record in self.list_records(type=type, name=name)]
        if current_values != [content]:
            # a change is necessary
            url = '/domains/{0}/records/{1}/{2}'.format(self.domain_id, self._relative_name(name), type)
            if current_values:
                record = {'rrset_values': current_values + [content]}
                self._put(url, record)
            else:
                record = {'rrset_values': [content]}
                # add the ttl, if this is a new record
                if self.options.get('ttl'):
                    record['rrset_ttl'] = self.options.get('ttl')
                self._post(url, record)
        LOGGER.debug('create_record: %s', True)
        return True

    def list_records(self, type=None, name=None, content=None):
        if (self.protocol == 'RPC'):
            return self.rpc_helper.list_records(type, name, content)

        try:
            if name is not None:
                if type is not None:
                    query_results = [self._get(
                        '/domains/{0}/records/{1}/{2}'
                        .format(self.domain_id, self._relative_name(name), type))]
                else:
                    query_results = self._get('/domains/{0}/records/{1}'
                                              .format(self.domain_id, self._relative_name(name)))
            else:
                query_results = self._get('/domains/{0}/records'.format(self.domain_id))
                if type is not None:
                    query_results = [item for item in query_results if item['type'] == type]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                query_results = []
            else:
                raise
        # convert records with multiple values into single-value records
        records = []
        for query_result in query_results:
            for value in query_result['rrset_values']:
                record = {
                    'type': query_result['rrset_type'],
                    'name': self._fqdn_name(query_result['rrset_name']),
                    'ttl': query_result['rrset_ttl'],
                    'content': value,
                    'id': query_result['rrset_name'],
                }
                # cleanup potential quoting if suitable
                self._clean_TXT_record(record)
                records.append(record)
        # filter for content, if requested
        if content is not None:
            records = [record for record in records if record['content'] == content]
        LOGGER.debug('list_records: %s', records)
        return records

    def update_record(self, identifier, type=None, name=None, content=None):
        if (self.protocol == 'RPC'):
            return self.rpc_helper.update_record(identifier, type, name, content)

        data = {}
        if type:
            data['rrset_type'] = type
        if name:
            data['rrset_name'] = self._relative_name(name)
        if content:
            if isinstance(content, (list, tuple, set)):
                data['rrset_values'] = list(content)
            else:
                data['rrset_values'] = [content]
        if type is None:
            # replace the records of a specific type
            url = '/domains/{0}/records/{1}/{2}'.format(self.domain_id,
                                                        identifier or self._relative_name(name),
                                                        type)
            self._put(url, data)
        else:
            # replace all records with a matching name
            url = '/domains/{0}/records/{1}'.format(self.domain_id,
                                                    identifier or self._relative_name(name))
            self._put(url, {'items': [data]})
        LOGGER.debug('update_record: %s', True)
        return True

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if (self.protocol == 'RPC'):
            return self.rpc_helper.delete_record(identifier, type, name, content)

        remove_count = 0
        if not identifier:
            # get all matching (by type and name) records - ignore 'content' for now
            records = self.list_records(type=type, name=name)
            for current_type in set(record['type'] for record in records):
                matching_records = [record for record in records if record['type'] == current_type]
                # collect all non-matching values
                if content is None:
                    remaining_values = []
                else:
                    remaining_values = [record['content'] for record in matching_records
                                        if record['content'] != content]
                url = '/domains/{0}/records/{1}/{2}'.format(
                    self.domain_id, self._relative_name(name), current_type)
                if len(matching_records) == len(remaining_values):
                    # no matching item should be removed for this type
                    pass
                elif remaining_values:
                    # reduce the list of values
                    self._put(url, {'rrset_values': remaining_values})
                    remove_count += 1
                else:
                    # remove the complete record (possibly with multiple values)
                    self._delete(url)
                    remove_count += 1
        else:
            self._delete('/domains/{0}/records/{1}'.format(self.domain_id, identifier))
        if remove_count == 0:
            raise Exception('Record identifier could not be found.')

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug('delete_record: %s', True)
        return True           

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Api-Key': self.options.get('auth_token')
        }
        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        r = requests.request(action, url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        if action == 'DELETE':
            return ''
        else:
            return r.json()

class GandiRPCSubProvider(object):

    # This exception is for cleaner handling of internal errors
    # within the Gandi provider codebase
    class GandiInternalError(Exception):
        """Internal exception handling class for Gandi management errors"""
        pass

    def __init__(self, api_key, api_endpoint, domain, relative_name_fn, full_name_fn):
        super(GandiRPCSubProvider, self).__init__()

        self._api_endpoint = api_endpoint
        self._api_key = api_key
        self._domain = domain
        self._relative_name = relative_name_fn
        self._full_name = full_name_fn
        self._api = xmlrpclib.ServerProxy(self._api_endpoint, allow_none=True)

    def authenticate(self):
        try:
            payload = self._api.domain.info(self._api_key, self._domain)
            self._zone_id = payload['zone_id']
            return payload['id']
        except xmlrpclib.Fault as err:
            raise Exception("Failed to authenticate: '{0}'".format(err))

    def create_record(self, type, name, content, ttl):
        version = None
        ret = False

        # This isn't quite "do nothing" if the record already exists.
        # In this case, no new record will be created, but a new zone version
        # will be created and set.
        try:
            version = self._api.domain.zone.version.new(self._api_key, self._zone_id)
            self._api.domain.zone.record.add(self._api_key, self._zone_id, version,
                                            {'type': type.upper(),
                                             'name': name,
                                             'value': content,
                                             'ttl': ttl
                                            })
            self._api.domain.zone.version.set(self._api_key, self._zone_id, version)
            ret = True

        finally:
            if not ret and version is not None:
                self._api.domain.zone.version.delete(self._api_key, self._zone_id, version)

        LOGGER.debug("create_record: %s", ret)
        return ret

    def list_records(self, type=None, name=None, content=None):
        opts = {}
        if type is not None:
            opts['type'] = type.upper()
        if name is not None:
            opts['name'] = self._relative_name(name)
        if content is not None:
            opts['value'] = self._txt_encode(content) if opts.get('type', '') == 'TXT' else content

        records = []
        payload = self._api.domain.zone.record.list(self._api_key, self._zone_id, 0, opts)
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': self._full_name(record['name']),
                'ttl': record['ttl'],
                'content': record['value'],
                'id': record['id']
            }

            # Gandi will add quotes to all TXT record strings
            if processed_record['type'] == 'TXT':
                processed_record['content'] = self._txt_decode(processed_record['content'])

            records.append(processed_record)

        LOGGER.debug("list_records: %s", records)
        return records

    def update_record(self, identifier, type=None, name=None, content=None):      
        if not identifier:
            records = self.list_records(type, name)
            if len(records) == 1:
                identifier = records[0]['id']
            elif len(records) > 1:
                raise Exception('Several record identifiers match the request')
            else:
                raise Exception('Record identifier could not be found')

        identifier = int(identifier)
        version = None

        # Gandi doesn't allow you to edit records on the active zone file.
        # Gandi also doesn't persist zone record identifiers when creating
        # a new zone file. To update by identifier, we lookup the record
        # by identifier, then use the record fields to find the record in
        # the newly created zone.
        records = self._api.domain.zone.record.list(self._api_key, self._zone_id, 0, {'id': identifier})

        if len(records) == 1:
            rec = records[0]
            del rec['id']

            try:
                version = self._api.domain.zone.version.new(self._api_key, self._zone_id)
                records = self._api.domain.zone.record.list(self._api_key, self._zone_id, version, rec)
                if len(records) != 1:
                    raise self.GandiInternalError("expected one record")

                if type is not None:
                    rec['type'] = type.upper()
                if name is not None:
                    rec['name'] = self._relative_name(name)
                if content is not None:
                    rec['value'] = self._txt_encode(content) if rec['type'] == 'TXT' else content

                records = self._api.domain.zone.record.update(self._api_key,
                                                             self._zone_id,
                                                             version,
                                                             {'id': records[0]['id']},
                                                             rec)
                if len(records) != 1:
                    raise self.GandiInternalError("expected one updated record")

                self._api.domain.zone.version.set(self._api_key, self._zone_id, version)
                ret = True

            except self.GandiInternalError:
                pass

            finally:
                if not ret and version is not None:
                    self._api.domain.zone.version.delete(self._api_key, self._zone_id, version)

        LOGGER.debug("update_record: %s", ret)
        return ret

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        version = None
        ret = False

        opts = {}
        if identifier is not None:
            opts['id'] = identifier
        else:
            opts['type'] = type.upper()
            opts['name'] = self._relative_name(name)
            opts["value"] = self._txt_encode(content) if opts['type'] == 'TXT' else content

        records = self._api.domain.zone.record.list(self._api_key, self._zone_id, 0, opts)
        if len(records) == 1:
            rec = records[0]
            del rec['id']

            try:
                version = self._api.domain.zone.version.new(self._api_key, self._zone_id)
                cnt = self._api.domain.zone.record.delete(self._api_key, self._zone_id, version, rec)
                if cnt != 1:
                    raise self.GandiInternalError("expected one deleted record")

                self._api.domain.zone.version.set(self._api_key, self._zone_id, version)
                ret = True

            except self.GandiInternalError:
                pass

            finally:
                if not ret and version is not None:
                    self._api.domain.zone.version.delete(self._api_key, self._zone_id, version)

        LOGGER.debug("delete_record: %s", ret)
        return ret    

    @staticmethod
    def _txt_encode(val):
        return ''.join(['"', val.replace('\\', '\\\\').replace('"', '\\"'), '"'])

    @staticmethod
    def _txt_decode(val):
        if len(val) > 1 and val[0:1] == '"':
            val = val[1:-1].replace('" "', '').replace('\\"', '"').replace('\\\\', '\\')
        return val

