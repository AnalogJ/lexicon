"""
To set enable live testing against the Exoscale API.

* create an account
* subscribe to DNS (with 1 domain)
* create a domain called "lexicontest.com"

Set the following environment variables.

    export LEXICON_EXOSCALE_KEY=EXO...
    export LEXICON_EXOSCALE_SECRET=xxx

"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class ExoscaleProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Exoscale"""

    provider_name = "exoscale"
    domain = "lexicontest.com"

    def _filter_headers(self):
        return ["X-DNS-Token", "x-request-id"]
