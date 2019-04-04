"""Integration tests for Aurora"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class AuroraProviderTests(TestCase, IntegrationTests):
    """TestCase for Aurora"""
    provider_name = 'aurora'
    domain = 'example.nl'

    def _filter_headers(self):
        return ['Authorization']
