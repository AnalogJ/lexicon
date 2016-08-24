class Provider(object):
    def __init__(self, options):
        self.provider_name = 'example',
        self.options = options
        self.default_ttl = 3600

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider, so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason, of if the domain does not exist.
    def authenticate(self):
        raise NotImplementedError("Providers should implement this!")

    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        raise NotImplementedError("Providers should implement this!")

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")

    # Update a record. Identifier must be specified.
    def update_record(self, identifier, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        raise NotImplementedError("Providers should implement this!")


    #Helpers
    def _get(self, url='/', query_params=None):
        return self._request('GET', url, query_params=query_params)

    def _post(self, url='/', data=None, query_params=None):
        return self._request('POST', url, data=data, query_params=query_params)

    def _put(self, url='/', data=None, query_params=None):
        return self._request('PUT', url, data=data, query_params=query_params)

    def _delete(self, url='/', query_params=None):
        return self._request('DELETE', url, query_params=query_params)

    def _fqdn_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if not record_name.endswith(self.options['domain']):
            record_name = "{0}.{1}".format(record_name, self.options['domain'])
        return "{0}.".format(record_name) #return the fqdn name

    def _full_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if not record_name.endswith(self.options['domain']):
            record_name = "{0}.{1}".format(record_name, self.options['domain'])
        return record_name

    def _relative_name(self, record_name):
        record_name = record_name.rstrip('.') # strip trailing period from fqdn if present
        #check if the record_name is fully specified
        if record_name.endswith(self.options['domain']):
            record_name = record_name[:-len(self.options['domain'])]
            record_name = record_name.rstrip('.')
        return record_name

    def _clean_TXT_record(self, record):
        if record['type'] == 'TXT':
            # some providers have quotes around the TXT records, so we're going to remove those extra quotes
            record['content'] = record['content'][1:-1]
        return record
