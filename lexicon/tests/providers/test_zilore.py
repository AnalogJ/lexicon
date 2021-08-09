"""Integration tests for Zilore"""
from unittest import TestCase

from lexicon.providers.zilore import Provider
from lexicon.tests.providers import integration_tests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class ZiloreProviderTests(TestCase, integration_tests.IntegrationTestsV2):
    """TestCase for Zilore"""

    Provider = Provider
    provider_name = "zilore"
    domain = "full4ir.tk"

    def _filter_headers(self):
        return ["X-Auth-Key"]

    # We override this test because Zilore refuses to create a A record with '127.0.0.1' value.
    @integration_tests._vcr_integration_test
    def test_provider_when_calling_create_record_for_A_with_valid_name_and_content(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("A", "localhost", "1.1.1.1")
