from __future__ import absolute_import

from lexicon.config import ConfigResolver, legacy_config_resolver


class Provider(object):
    """
    This is the base class for all lexicon Providers.
    It provides common functionality and ensures that all implemented
    Providers follow a standard ducktype.
    All standardized options will be provided here as defaults, but can be overwritten
    by environmental variables and cli arguments.

    Common options are:

    action
    domain
    type
    name
    content
    ttl
    priority
    identifier

    The provider_env_cli_options will also contain any Provider specific options:

    auth_username
    auth_token
    auth_password
    ...

    :param config: is a ConfigResolver object that contains all the options
    for this provider, merged from CLI and Env variables.
    """

    def __init__(self, config):
        if not isinstance(config, ConfigResolver):
            # If config is a plain dict, we are in a legacy situation.
            # To protect the Provider API, the legacy dict is handled in a
            # correctly defined ConfigResolver.
            self.config = legacy_config_resolver(config)
        else:
            self.config = config

        # Default ttl
        self.config.with_dict({'ttl': 3600})

        self.provider_name = self.config.resolve(
            'lexicon:provider_name') or self.config.resolve('lexicon:provider')
        self.domain = self.config.resolve('lexicon:domain')
        self.domain_id = None

    # Provider API
    def authenticate(self):
        """
        Authenticate against provider,
        Make any requests required to get the domain's id for this provider,
        so it can be used in subsequent calls.
        Should throw an error if authentication fails for any reason,
        of if the domain does not exist.
        """
        return self._authenticate()

    def create_record(self, type, name, content):
        """
        Create record. If record already exists with the same content, do nothing.
        """
        return self._create_record(type, name, content)

    def list_records(self, type=None, name=None, content=None):
        """
        List all records. Return an empty list if no records found
        type, name and content are used to filter records.
        If possible filter during the query, otherwise filter after response is received.
        """
        return self._list_records(type=type, name=name, content=content)

    def update_record(self, identifier, type=None, name=None, content=None):
        """
        Update a record. Identifier must be specified.
        """
        return self._update_record(identifier, type=type, name=name, content=content)

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        """
        Delete an existing record.
        If record does not exist, do nothing.
        If an identifier is specified, use it, otherwise do a lookup using type, name and content.
        """
        return self._delete_record(identifier=identifier, type=type, name=name, content=content)

    # Internal abstract implementations
    def _authenticate(self):
        raise NotImplementedError("Providers should implement this!")

    def _create_record(self, type, name, content):
        raise NotImplementedError("Providers should implement this!")

    def _list_records(self, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")

    def _update_record(self, identifier, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")

    def _delete_record(self, identifier=None, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")

    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        raise NotImplementedError("Providers should implement this!")

    def _get(self, url='/', query_params=None):
        return self._request('GET', url, query_params=query_params)

    def _post(self, url='/', data=None, query_params=None):
        return self._request('POST', url, data=data, query_params=query_params)

    def _put(self, url='/', data=None, query_params=None):
        return self._request('PUT', url, data=data, query_params=query_params)

    def _delete(self, url='/', query_params=None):
        return self._request('DELETE', url, query_params=query_params)

    def _fqdn_name(self, record_name):
        # strip trailing period from fqdn if present
        record_name = record_name.rstrip('.')
        # check if the record_name is fully specified
        if not record_name.endswith(self.domain):
            record_name = "{0}.{1}".format(record_name, self.domain)
        return "{0}.".format(record_name)  # return the fqdn name

    def _full_name(self, record_name):
        # strip trailing period from fqdn if present
        record_name = record_name.rstrip('.')
        # check if the record_name is fully specified
        if not record_name.endswith(self.domain):
            record_name = "{0}.{1}".format(record_name, self.domain)
        return record_name

    def _relative_name(self, record_name):
        # strip trailing period from fqdn if present
        record_name = record_name.rstrip('.')
        # check if the record_name is fully specified
        if record_name.endswith(self.domain):
            record_name = record_name[:-len(self.domain)]
            record_name = record_name.rstrip('.')
        return record_name

    def _clean_TXT_record(self, record):
        if record['type'] == 'TXT':
            # Some providers have quotes around the TXT records,
            # so we're going to remove those extra quotes
            record['content'] = record['content'][1:-1]
        return record

    def _get_lexicon_option(self, option):
        return self.config.resolve('lexicon:{0}'.format(option))

    def _get_provider_option(self, option):
        return self.config.resolve('lexicon:{0}:{1}'.format(self.provider_name, option))
