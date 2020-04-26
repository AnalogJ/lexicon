"""Integration tests for UltraDNS"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class UltradnsProviderTests(TestCase, IntegrationTests):
    """TestCase for UltraDNS"""
    provider_name = 'ultradns'
    domain = 'example-abtest.com'

    def _filter_headers(self):
        return ['Authorization']

    def _filter_post_data_parameters(self):
        return ['username', 'password', 'accessToken']
