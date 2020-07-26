"""Integration tests for HostingDE provider"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class FooProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for hostingde provider"""

    provider_name = "hostingde"
    domain = "eruza.de"

    def _filter_post_data_parameters(self):
        return ["authToken"]

    def _filter_headers(self):
        return ["Authorization"]

    def _filter_query_parameters(self):
        return ["secret_key"]
