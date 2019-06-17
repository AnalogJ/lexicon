"""Module provider for DirectAdmin hosts"""
from lexicon.providers.base import Provider as BaseProvider

def provider_parser(subparser):
    """Return the parser for this provider"""
    subparser.add_argument(
        "--endpoint",
        help = "specify the DirectAdmin endpoint"
    )

class Provider(BaseProvider):
    """Provider class for DirectAdmin"""
    def __init__(self, config):
        super(Provider, self).__init__(config)

        self.endpoint = self._get_provider_option('endpoint')
        if self.endpoint is None:
            raise Exception('Specify endpoint of DirectAdmin')

    def _authenticate(self):
        None

    def _create_record(self, rtype, name, content):
        None

    def _list_records(self, rtype=None, name=None, content=None):
        None

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        None

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        None

    def _request(self, action='GET', url='/', data={}, query_params={}):
        None
