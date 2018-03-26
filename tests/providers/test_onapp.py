from unittest import TestCase
from lexicon.providers.onapp import Provider
from integration_tests import IntegrationTests

class OnappProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'onapp'
    domain = 'my-test.org'

    def _filter_headers(self):
        return ['Authorization']

    def _test_options(self):
        options = super(OnappProviderTests, self)._test_options()
        options.update({'auth_server':'https://dashboard.dynomesh.com.au'})
        return options
