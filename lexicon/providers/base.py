class Provider(object):
    def __init__(self, options):
        self.provider_name = 'example',
        self.options = options

    # Authenicate against provider,
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