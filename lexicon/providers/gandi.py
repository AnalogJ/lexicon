"""Provide support to Lexicon for Gandi DNS changes.

Lexicon provides a common interface for querying and managing DNS services
through those services' APIs. This module implements the Lexicon interface
against the Gandi API.

The Gandi API is different from typical DNS APIs in that Gandi
zone changes are atomic. You cannot edit the currently active
configuration. Any changes require editing either a new or inactive
configuration. Once the changes are committed, then the domain is switched
to using the new zone configuration. This module makes no attempt to
cleanup previous zone configurations.

Note that Gandi domains can share zone configurations. In other words,
I can have domain-a.com and domain-b.com which share the same zone
configuration file. If I make changes to domain-a.com, those changes
will only apply to domain-a.com, as domain-b.com will continue using
the previous version of the zone configuration. This module makes no
attempt to detect and account for that.


"""

import xmlrpclib
from lexicon.providers.base import Provider as BaseProvider


def ProviderParser(subparser):
    """Specify arguments for Gandi Lexicon Provider."""
    subparser.add_argument('--auth-token', help="specify Gandi API key")


class Provider(BaseProvider):
    """Provide Gandi DNS API implementation of Lexicon Provider interface.

    The class will use the following environment variables to configure
    it instance. For more information, read the Lexicon documentation.

    - LEXICON_GANDI_API_ENDPOINT - the Gandi API endpoint to use
      The default is the production URL https://rpc.gandi.net/xmlrpc/.
      Set this environment variable to the OT&E URL for testing.

    """

    def __init__(self, options, provider_options=None):
        """Initialize Gandi DNS provider."""

        super(Provider, self).__init__(options)

        if provider_options is None:
            provider_options = {}

        api_endpoint = provider_options.get('api_endpoint') or 'https://rpc.gandi.net/xmlrpc/'

        self.apikey = self.options['auth_token']
        self.api = xmlrpclib.ServerProxy(api_endpoint)

        # self.domain_id is required by test suite
        self.domain_id = None
        self.zone_id = None

        self.domain = self.options['domain'].lower()

    # Authenicate against provider,
    # Make any requests required to get the domain's id for this provider,
    # so it can be used in subsequent calls. Should throw an error if
    # authentication fails for any reason, or if the domain does not exist.
    def authenticate(self):
        """Determine the current domain and zone IDs for the domain."""

        try:
            payload = self.api.domain.info(self.apikey, self.domain)
            self.domain_id = payload['id']
            self.zone_id = payload['zone_id']

        except xmlrpclib.Fault as err:
            raise StandardError("Failed to authenticate: '{0}'".format(err))

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        """Creates a record for the domain in a new Gandi zone."""

        version = None
        ret = False

        name = self._canonicalize_name(name)

        # This isn't quite "do nothing" if the record already exists.
        # In this case, no new record will be created, but a new zone version
        # will be created and set.
        try:
            version = self.api.domain.zone.version.new(self.apikey, self.zone_id)
            self.api.domain.zone.record.add(self.apikey, self.zone_id, version,
                                            {'type': type.upper(),
                                             'name': name,
                                             'value': content})
            self.api.domain.zone.version.set(self.apikey, self.zone_id, version)
            ret = True

        finally:
            if not ret and version is not None:
                self.api.domain.zone.version.delete(self.apikey, self.zone_id, version)

        print "create_record: {0}".format(ret)
        return ret

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        """List all record for the domain in the active Gandi zone."""

        opts = {}
        if type is not None:
            opts['type'] = type.upper()
        if name is not None:
            opts['name'] = self._canonicalize_name(name)
        if content is not None:
            opts['value'] = self._txt_encode(content) if opts.get('type', '') == 'TXT' else content

        records = []
        payload = self.api.domain.zone.record.list(self.apikey, self.zone_id, 0, opts)
        for record in payload:
            processed_record = {
                'type': record['type'],
                'name': self._fqdn(record['name']),
                'ttl': record['ttl'],
                'content': record['value'],
                'id': record['id']
            }

            # Gandi will add quotes to all TXT record strings
            if processed_record['type'] == 'TXT':
                processed_record['content'] = self._txt_decode(processed_record['content'])

            records.append(processed_record)

        print "list_records: {0}".format(records)
        return records

    # Update a record. Identifier must be specified.
    def update_record(self, identifier, type=None, name=None, content=None):
        """Updates the specified record in a new Gandi zone."""

        identifier = int(identifier)
        version = None

        # Gandi doesn't allow you to edit records on the active zone file.
        # Gandi also doesn't persist zone record identifiers when creating
        # a new zone file. To update by identifier, we lookup the record
        # by identifier, then use the record fields to find the record in
        # the newly created zone.
        records = self.api.domain.zone.record.list(self.apikey, self.zone_id, 0, {'id': identifier})

        if len(records) == 1:
            rec = records[0]
            del rec['id']

            try:
                version = self.api.domain.zone.version.new(self.apikey, self.zone_id)
                records = self.api.domain.zone.record.list(self.apikey, self.zone_id, version, rec)
                if len(records) != 1:
                    raise GandiInternalError("expected one record")

                if type is not None:
                    rec['type'] = type.upper()
                if name is not None:
                    rec['name'] = self._canonicalize_name(name)
                if content is not None:
                    rec['value'] = self._txt_encode(content) if rec['type'] == 'TXT' else content

                records = self.api.domain.zone.record.update(self.apikey,
                                                             self.zone_id,
                                                             version,
                                                             {'id': records[0]['id']},
                                                             rec)
                if len(records) != 1:
                    raise GandiInternalError("expected one updated record")

                self.api.domain.zone.version.set(self.apikey, self.zone_id, version)
                ret = True

            except GandiInternalError:
                pass

            finally:
                if not ret and version is not None:
                    self.api.domain.zone.version.delete(self.apikey, self.zone_id, version)

        print "update_record: {0}".format(ret)
        return ret

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        """Removes the specified record in a new Gandi zone."""

        version = None
        ret = False

        opts = {}
        if identifier is not None:
            opts['id'] = identifier
        else:
            opts['type'] = type.upper()
            opts['name'] = self._canonicalize_name(name)
            opts["value"] = self._txt_encode(content) if opts['type'] == 'TXT' else content

        records = self.api.domain.zone.record.list(self.apikey, self.zone_id, 0, opts)
        if len(records) == 1:
            rec = records[0]
            del rec['id']

            try:
                version = self.api.domain.zone.version.new(self.apikey, self.zone_id)
                cnt = self.api.domain.zone.record.delete(self.apikey, self.zone_id, version, rec)
                if cnt != 1:
                    raise GandiInternalError("expected one deleted record")

                self.api.domain.zone.version.set(self.apikey, self.zone_id, version)
                ret = True

            except GandiInternalError:
                pass

            finally:
                if not ret and version is not None:
                    self.api.domain.zone.version.delete(self.apikey, self.zone_id, version)

        print "delete_record: {0}".format(ret)
        return ret

    def _fqdn(self, name):
       if not name.endswith('.') and not name.endswith('.{0}'.format(self.domain)):
           name += '.{0}'.format(self.domain)
       return name

    def _canonicalize_name(self, name):
        name = name.lower()
        if name.endswith('.{0}.'.format(self.domain)):
            name = name[:-1]
        if name.endswith('.{0}'.format(self.domain)):
            name = name[:-(len(self.domain) + 1)]
        return name

    @staticmethod
    def _txt_encode(val):
        return ''.join(['"', val.replace('\\', '\\\\').replace('"', '\\"'), '"'])

    @staticmethod
    def _txt_decode(val):
        if len(val) > 1 and val[0:1] == '"':
            val = val[1:-1].replace('" "', '').replace('\\"', '"').replace('\\\\', '\\')
        return val


# This exception is for cleaner handling of internal errors
# within the Gandi provider codebase
class GandiInternalError(Exception):
    """Internal exception handling class for Gandi management errors"""

    pass
