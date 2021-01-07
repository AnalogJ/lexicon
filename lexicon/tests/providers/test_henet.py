"""Integration tests for Henet"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class HenetProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Henet"""

    provider_name = "henet"
    domain = "lexicontest.com"

    def _filter_post_data_parameters(self):
        return ["email", "pass"]

    def _filter_headers(self):
        return ["Authorization", "Cookie"]

    def _filter_query_parameters(self):
        return ["pass"]
