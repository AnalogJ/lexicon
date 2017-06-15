# Test for one implementation of the interface
from unittest import TestCase
from lexicon.providers.ovh import Provider
from integration_tests import IntegrationTests

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class OvhProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'ovh'
    domain = 'elogium.net'

    def _filter_headers(self):
        return ['X-Ovh-Application', 'X-Ovh-Consumer', 'X-Ovh-Signature']

    # Override _test_options to call env_auth_options and then import auth config from env variables
    def _test_options(self):
        cmd_options = super(OvhProviderTests, self)._test_options()
        cmd_options.update({'auth_entrypoint':'ovh-eu'})
        return cmd_options
