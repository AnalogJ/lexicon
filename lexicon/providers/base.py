"""Base provider module for all Lexicon providers"""
from __future__ import absolute_import
import warnings

from lexicon.config import ConfigResolver, legacy_config_resolver


class Provider(object):  # pylint: disable=useless-object-inheritance
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
            # Also, there may be some situation where `provider` key is not set in the config.
            # It should not happen when Lexicon is called from Client, as it will set itself
            # this key. However there were no automated logic if the Provider is used directly.
            # So we provide this logic here.
            if not config.get('provider_name') and not config.get('provider'):
                config['provider_name'] = __name__  # Obviously we use the module name itself.
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

    def create_record(self, rtype=None, name=None, content=None, **kwargs):
        """
        Create record. If record already exists with the same content, do nothing.
        """
        if not rtype and kwargs.get('type'):
            warnings.warn('Parameter "type" is deprecated, use "rtype" instead.',
                          DeprecationWarning)
            rtype = kwargs.get('type')

        return self._create_record(rtype, name, content)

    def list_records(self, rtype=None, name=None, content=None, **kwargs):
        """
        List all records. Return an empty list if no records found
        type, name and content are used to filter records.
        If possible filter during the query, otherwise filter after response is received.
        """

        if not rtype and kwargs.get('type'):
            warnings.warn('Parameter "type" is deprecated, use "rtype" instead.',
                          DeprecationWarning)
            rtype = kwargs.get('type')

        return self._list_records(rtype=rtype, name=name, content=content)

    def update_record(self, identifier, rtype=None, name=None, content=None, **kwargs):
        """
        Update a record. Identifier must be specified.
        """
        if not rtype and kwargs.get('type'):
            warnings.warn('Parameter "type" is deprecated, use "rtype" instead.',
                          DeprecationWarning)
            rtype = kwargs.get('type')

        return self._update_record(identifier, rtype=rtype, name=name, content=content)

    def delete_record(self, identifier=None, rtype=None, name=None, content=None, **kwargs):
        """
        Delete an existing record.
        If record does not exist, do nothing.
        If an identifier is specified, use it, otherwise do a lookup using type, name and content.
        """
        if not rtype and kwargs.get('type'):
            warnings.warn('Parameter "type" is deprecated, use "rtype" instead.',
                          DeprecationWarning)
            rtype = kwargs.get('type')

        return self._delete_record(identifier=identifier, rtype=rtype, name=name, content=content)

    # Internal abstract implementations
    def _authenticate(self):
        raise NotImplementedError("Providers must implement this!")

    def _create_record(self, rtype, name, content):
        raise NotImplementedError("Providers must implement this!")

    def _list_records(self, rtype=None, name=None, content=None):
        raise NotImplementedError("Providers must implement this!")

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        raise NotImplementedError("Providers must implement this!")

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        raise NotImplementedError("Providers must implement this!")

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        raise NotImplementedError("Providers must implement this!")

    # Helpers
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

    def _clean_TXT_record(self, record):  # pylint: disable=no-self-use,invalid-name
        if record['type'] == 'TXT':
            # Some providers have quotes around the TXT records,
            # so we're going to remove those extra quotes
            record['content'] = record['content'][1:-1]
        return record

    def _get_lexicon_option(self, option):
        return self.config.resolve('lexicon:{0}'.format(option))

    def _get_provider_option(self, option):
        return self.config.resolve('lexicon:{0}:{1}'.format(self.provider_name, option))
