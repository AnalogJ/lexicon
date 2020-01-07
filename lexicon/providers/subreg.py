"""Provide support to Lexicon for Subreg.cz DNS changes."""
from __future__ import absolute_import
from builtins import staticmethod

from lexicon.providers.gransy import Provider as GransyProvider, gransy_provider_parser

NAMESERVER_DOMAINS = []

def provider_parser(subparser):
    """Configure provider parser"""
    gransy_provider_parser(subparser)

    subparser.description = "Compatibility proxy for Gransy site subreg.cz. The Subreg " \
        "provider is deprecated, use Gransy provider instead."

class Provider(GransyProvider):
    """Provider class for Subreg"""

    @staticmethod
    def _raise_error(major, minor, message):
        raise SubregError(major, minor, message)

class SubregError(Exception):
    """Specific error for Subreg provider"""
    def __init__(self, major, minor, message):
        self.major = int(major)
        self.minor = int(minor)
        self.message = message
        super(SubregError, self).__init__()

    def __str__(self):
        return 'Major: {} Minor: {} Message: {}'.format(self.major, self.minor, self.message)
