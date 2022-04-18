"""Integration tests for DirectAdmin"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse the
# tests which *each and every* implementation of the interface must pass, by
# inheritance from integration_tests.IntegrationTests
class DirectAdminProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for DirectAdmin provider"""

    provider_name = "directadmin"
    domain = "example.com"
    endpoint = "http://localhost"

    def _filter_post_data_parameters(self):
        return []

    def _filter_headers(self):
        return ["Authorization"]

    def _filter_query_parameters(self):
        return []

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
        to filter the provider response."""
        return response

    def _test_parameters_overrides(self):
        return {"endpoint": self.endpoint}
