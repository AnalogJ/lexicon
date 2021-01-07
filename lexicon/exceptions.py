"""Lexicon exceptions module"""


class ProviderNotAvailableError(Exception):
    """
    Custom exception to raise when a provider is not available,
    typically because some optional dependencies are missing
    """
