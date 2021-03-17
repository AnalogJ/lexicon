"""Integration tests for Dynu.com"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class DynuProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Dynu.com"""

    provider_name = "dynu"
    domain = "example.com"

    def _filter_headers(self):
        return ["API-Key"]

    def _filter_response(self, response):
        if response["status"]["code"] not in [200, 503]:
            return None
        return response
