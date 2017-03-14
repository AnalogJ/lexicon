# Test for one implementation of the interface
from lexicon.providers.dnsimple import Provider
from integration_tests import IntegrationTests
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsimpleProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'dnsimple'
    domain = 'wopr.tech'
    provider_opts = {'api_endpoint': 'https://api.sandbox.dnsimple.com/v2'}
    def _filter_headers(self):
        return ['Authorization','set-cookie','X-Dnsimple-OTP']
