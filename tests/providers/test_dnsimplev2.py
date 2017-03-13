# Test for one implementation of the interface
from lexicon.providers.dnsimplev2 import Provider
from integration_tests import IntegrationTests
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class Dnsimplev2ProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'dnsimplev2'
    domain = 'wopr.tech'
    provider_opts = {'api_endpoint': 'https://api.sandbox.dnsimple.com/v2'}
    def _filter_headers(self):
        return ['Authorization','set-cookie']
    def _filter_post_data_parameters(self):
        return ['email']
