# Test for one implementation of the interface
from unittest import TestCase
from lexicon.providers.ovh import Provider
from lexicon.common.options_handler import env_auth_options
from integration_tests import IntegrationTests

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class OvhProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'ovh'
    domain = 'elogium.net'
    zoneFile = None

    def _filter_post_data_parameters(self):
        return ['login_token']

    def _filter_headers(self):
        return ['Authorization']

    def _filter_query_parameters(self):
        return ['application_key', 'application_secret', 'consumer_key']

    # Override _test_options to call env_auth_options and then import auth config from env variables
    def _test_options(self):
        cmd_options = env_auth_options(self.provider_name)
        cmd_options['domain'] = self.domain
        return cmd_options

    # Make a backup of the targeted zone before launching tests
    @classmethod
    def setUpClass(cls):
        cmd_options = env_auth_options(cls.provider_name)
        cmd_options['domain'] = cls.domain
        provider = Provider(cmd_options)
        cls.zoneFile = provider.ovh_client.get('/domain/zone/{0}/export'.format(cls.domain))
        print(cls.zoneFile)

    # Restore the targeted zone after all tests done
    @classmethod
    def tearDownClass(cls):
        print(cls.zoneFile)
        cmd_options = env_auth_options(cls.provider_name)
        cmd_options['domain'] = cls.domain
        provider = Provider(cmd_options)
        options = {
            'zoneFile': cls.zoneFile
        }
        provider.ovh_client.post('/domain/zone/{0}/import'.format(cls.domain), **options)
