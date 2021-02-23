# Test for one implementation of the interface
from unittest import TestCase

from lexicon.tests.providers import integration_tests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class MythicBeastsProviderTests(TestCase, integration_tests.IntegrationTestsV2):
    """Integration tests for Mythic Beasts provider"""

    provider_name = "mythicbeasts"
    domain = "lexitus.co.uk"

    def _filter_post_data_parameters(self):
        return ["access_token"]

    def _filter_headers(self):
        return ["Authorization"]

    # def _filter_query_parameters(self):
    #     return ['secret_key']

    # def _filter_response(self, response):
    #     """See `IntegrationTests._filter_response` for more information on how
    #     to filter the provider response."""
    #     return response

    def _test_fallback_fn(self):
        return lambda x: "placeholder_" + x if x not in ("auth_token") else ""

    # We override this test because Mythic Beasts refuse to create a A record with 'localhost' value.
    #  - no - this is ok - problem with pre-existing records
    # @integration_tests._vcr_integration_test
    # def test_provider_when_calling_create_record_for_A_with_valid_name_and_content(
    #     self,
    # ):
    #     provider = self._construct_authenticated_provider()
    #     assert provider.create_record("A", "localhost2", "127.0.0.1")