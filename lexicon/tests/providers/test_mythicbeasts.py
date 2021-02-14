# Test for one implementation of the interface
from lexicon.tests.providers.integration_tests import IntegrationTestsV2
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class MythicBeastsProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Mythic Beasts provider"""
    provider_name = 'mythicbeasts'
    domain = 'lexitus.co.uk'
    def _filter_post_data_parameters(self):
        return ['login_token']

    def _filter_headers(self):
        return ['Authorization']

    def _filter_query_parameters(self):
        return ['secret_key']

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
        to filter the provider response."""
        return response