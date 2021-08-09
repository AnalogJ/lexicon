"""Integration tests for Vercel"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class VercelProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Vercel"""

    provider_name = "vercel"
    domain = "fullcr1stal.tk"

    def _filter_headers(self):
        return ["Authorization"]
