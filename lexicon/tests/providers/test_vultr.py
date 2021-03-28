"""Integration tests for Vultr"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class VultrProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Vultr"""

    provider_name = "vultr"
    domain = "lexicon-test.eu"

    def _filter_headers(self):
        return ["Authorization"]
