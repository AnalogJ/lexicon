# Test for one implementation of the interface
import os
from unittest import TestCase

import pytest
from lexicon.providers.exoscale import Provider

from integration_tests import IntegrationTests

"""
To set enable live testing against the Exoscale API.

* create an account
* subscribe to DNS (with 1 domain)
* create a domain called "lexicontest.com"

Set the following environment variables.

    export LEXICON_EXOSCALE_KEY=EXO...
    export LEXICON_EXOSCALE_SECRET=xxx

"""


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class ExoscaleProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = "exoscale"
    domain = "lexicontest.com"

    def _filter_headers(self):
        return ["X-DNS-Token", "x-request-id"]
