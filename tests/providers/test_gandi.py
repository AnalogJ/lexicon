# Test for one implementation of the interface
from lexicon.providers.cloudflare import Provider
from integration_tests import IntegrationTests
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CloudflareProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'gandi'
    domain = 'capsulecd.com'
    provider_opts = {'api_endpoint': 'https://rpc.ote.gandi.net/xmlrpc/'}
