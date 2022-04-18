"""Lexicon exceptions module"""


class LexiconError(Exception):
    """
    Base Class for the Lexicon Exception hierarchy
    """


class ProviderNotAvailableError(LexiconError):
    """
    Custom exception to raise when a provider is not available,
    typically because some optional dependencies are missing
    """


class AuthenticationError(LexiconError):
    """
    Authentication to the provider failed, likely username, password or domain mismatch
    """
