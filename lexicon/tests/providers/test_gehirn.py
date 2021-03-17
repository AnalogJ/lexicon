"""Integration tests for Gehirn"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV1


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
# TODO: migrate to IntegrationTestsV2 and its extended test suite
class GehirnProviderTests(TestCase, IntegrationTestsV1):
    """TestCase for Gehirn"""

    provider_name = "gehirn"
    domain = "example.com"

    def _filter_headers(self):
        return ["Authorization"]
