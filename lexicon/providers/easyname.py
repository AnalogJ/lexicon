from __future__ import absolute_import
from __future__ import print_function

from .base import Provider as BaseProvider

def ProviderParser(subparser):
    subparser.description = """A provider for Easyname DNS."""
    subparser.add_argument(
        '--auth-username',
        help='Specify username used to authenticate'
    )
    subparser.add_argument(
        '--auth-password',
        help='Specify password used to authenticate',
    )


class Provider(BaseProvider):
    """
        easyname provider
    """

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
