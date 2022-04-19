"""Compatibility layer for Zeit (old name for Vercel)"""
import logging

from lexicon.providers.vercel import NAMESERVER_DOMAINS  # noqa: F401
from lexicon.providers.vercel import provider_parser  # noqa: F401
from lexicon.providers.vercel import Provider as VercelProvider

LOGGER = logging.getLogger(__name__)


class Provider(VercelProvider):
    """Provider for Zeit"""

    def __init__(self, config):
        LOGGER.error(
            "Zeit provider is deprecated and will be removed in a future version of Lexicon."
        )
        LOGGER.error("Please use Vercel provider instead.")
        super().__init__(config)
