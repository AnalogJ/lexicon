# Test for one implementation of the interface
from unittest import TestCase

from integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class PorkbunProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Porkbun provider"""

    provider_name = "porkbun"

    # To make the live tests work, set this to a real domain registered with Porkbun,
    # and set the LEXICON_PORKBUN_AUTH_KEY and LEXICON_PORKBUN_AUTH_SECRET environment
    # variables appropriately (using your pk1 and sk1 API key values). You must also
    # rm -rf tests/fixtures/cassettes/porkbun/IntegrationTests, as otherwise the
    # previous recorded test data will be used, even with LEXICON_LIVE_TESTS=true.
    domain = "example.xyz"

    # If you've run the live tests before, you'll also need to delete any DNS entries
    # on your domain left over from previous test runs, as some tests will fail if
    # certain records exist when they run.
    #
    # For example, test_provider_when_calling_update_record_should_modify_record will
    # fail with a 400 on the update_record call if the destination "updated.test" TXT
    # record already exists from a previous live test run.

    # Once the tests complete successfully, you'll probably want to scrub anything
    # sensitive from the recorded data. Something like this works well:
    # find tests/fixtures/cassettes/porkbun/ -type f -exec sed -i 's/sensitive/sanitized/g' {} +

    def _filter_post_data_parameters(self):
        return ["login_token", "apikey", "secretapikey"]

    def _filter_headers(self):
        return ["Authorization"]

    def _filter_query_parameters(self):
        return ["secret_key"]

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
        to filter the provider response."""

        # Filter out any 503's - they aren't important and just clutter the recordings
        if response["status"]["code"] == 503:
            return None

        return response
