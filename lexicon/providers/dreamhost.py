
from base import Provider as BaseProvider

from dreamhostapi import DreamHostAPI


def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify token used authenticate")

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)
        self.api = None

    # Authenicate against provider,
    # Make any requests required to get the domain's id for this provider, so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason, of if the domain does not exist.
    def authenticate(self):
        self.api = DreamHostAPI(self.options['auth_token'])

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
	dhrecords = self.api.dns.list_records()
        records = []
        for record in dhrecords:
            remapped = {
                'type': record['type'],
                'name': record['record'],
                'content': record['value'],
            }
            records.append(remapped)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == name]
        if content:
            records = [record for record in records if record['content'] == content]

        print 'list_records: {0}'.format(records)
        return records
