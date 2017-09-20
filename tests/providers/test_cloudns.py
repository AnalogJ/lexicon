# Test for one implementation of the interface
from lexicon.providers.cloudns import Provider
from lexicon.common.options_handler import env_auth_options
from integration_tests import IntegrationTests
from unittest import TestCase


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CloudnsProviderTests(TestCase, IntegrationTests):
    Provider = Provider
    provider_name = 'cloudns'
    domain = 'api-example.com'

    def _filter_query_parameters(self):
        return ['auth-id', 'sub-auth-id', 'sub-auth-user', 'auth-password']

    def _filter_post_data_parameters(self):
        return ['auth-id', 'sub-auth-id', 'sub-auth-user', 'auth-password']

    # Override _test_options to call env_auth_options and then import auth config from env variables
    def _test_options(self):
        cmd_options = super(CloudnsProviderTests, self)._test_options()
        cmd_options.update(env_auth_options(self.provider_name))
        return cmd_options
