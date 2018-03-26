""""Test for rackspace implementation of the lexicon interface"""
from unittest import TestCase
import pytest

from lexicon.providers.rackspace import Provider
from integration_tests import IntegrationTests

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class RackspaceProviderTests(TestCase, IntegrationTests):
    """Tests the rackspace provider"""

    Provider = Provider
    provider_name = 'rackspace'
    domain = 'capsulecd.com'

    def _filter_post_data_parameters(self):
        return ['auth']

    def _filter_headers(self):
        return ['X-Auth-Token']

    # Rackspace does not provide a sandbox API; actual credentials are required
    # Replace the auth_account, auth_username and auth_api_key as well as the
    # domain above with an actual domain you have added to Rackspace to
    # regenerate the fixtures
    def _test_options(self):
        options = super(RackspaceProviderTests, self)._test_options()
        options.update({
            # 'auth_account': '123456',
            # 'auth_username': 'foo',
            # 'auth_api_key': 'bar',
            'sleep_time': '0'
        })
        options['auth_token'] = None
        return options

    @pytest.fixture(autouse=True)
    def skip_suite(self, request):
        if request.node.get_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')