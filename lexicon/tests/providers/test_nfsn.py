"""
Some small info about running live tests.

NFSN doesn't have trial accounts, so these tests can only
be run by those with an NFSN account. NFSN also requires
you to have an API key. More info here:

https://members.nearlyfreespeech.net/wiki/API/Introduction

You'll need an account to access that page.

Therefore, the following
parameters must be provided:

- LEXICON_NFSN_USERNAME -> Your NFSN username
- LEXICON_NFSN_TOKEN -> Your API Key
- LEXICON_NFSN_DOMAIN -> Domain you want to test with
"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class NFSNProviderTests(TestCase, IntegrationTests):
    """TestCase for NFSN"""
    provider_name = 'nfsn'
    domain = 'koupia.xyz'

    def _filter_headers(self):
        return ['X-NFSN-Authentication']
