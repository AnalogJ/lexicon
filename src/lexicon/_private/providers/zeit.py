"""Compatibility layer for Zeit (old name for Vercel)"""

import logging

from lexicon._private.providers.vercel import Provider as VercelProvider

LOGGER = logging.getLogger(__name__)


class Provider(VercelProvider):
    """Provider for Zeit"""

    def __init__(self, config):
        LOGGER.error(
            "Zeit provider is deprecated and will be removed in a future version of Lexicon."
        )
        LOGGER.error("Please use Vercel provider instead.")
        super().__init__(config)
