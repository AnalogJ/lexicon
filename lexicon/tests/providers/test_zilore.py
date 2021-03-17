"""Integration tests for Zilore"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests, _vcr_integration_test  # pylint: disable=protected-access
from lexicon.providers.zilore import Provider


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class ZiloreProviderTests(TestCase, IntegrationTests):
    """TestCase for Zeit"""
    Provider = Provider
    provider_name = 'zilore'
    domain = 'full4ir.tk'

    def _filter_headers(self):
        return ['X-Auth-Key']

    # We override this test because Zilore refuses to create a A record with '127.0.0.1' value.
    @_vcr_integration_test
    def test_provider_when_calling_create_record_for_A_with_valid_name_and_content(self):  # pylint: disable=invalid-name
        provider = self._construct_authenticated_provider()
        assert provider.create_record('A', 'localhost', '1.1.1.1')
