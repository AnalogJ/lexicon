# Test for one implementation of the interface
from lexicon.providers.nfsn import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

import os

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

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests


class NFSNProviderTests(TestCase, IntegrationTests):
    Provider = Provider
    provider_name = 'nfsn'
    domain = 'koupia.xyz'

    def _filter_headers(self):
        return ['X-NFSN-Authentication']
