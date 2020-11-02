""""Test for rackspace implementation of the lexicon interface"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class RackspaceProviderTests(TestCase, IntegrationTestsV2):
    """Tests the rackspace provider"""

    provider_name = "rackspace"
    domain = "capsulecd.com"

    def _filter_post_data_parameters(self):
        return ["auth"]

    def _filter_headers(self):
        return ["X-Auth-Token"]

    # Rackspace does not provide a sandbox API; actual credentials are required
    # Replace the auth_account, auth_username and auth_api_key as well as the
    # domain above with an actual domain you have added to Rackspace to
    # regenerate the fixtures
    def _test_parameters_overrides(self):
        # Set this to 1 if you are making new recordings and set to 0 when
        # finished to make sure we don't actually sleep and waste time
        # when we are replaying. Rackspace API calls are async, so you place
        # the initial request and then make update calls to see if the action
        # is complete and has a response.
        return {"sleep_time": "0"}

    def _test_fallback_fn(self):
        return lambda x: "placeholder_" + x if x != "auth_token" else None
