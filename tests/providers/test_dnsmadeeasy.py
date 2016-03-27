# Test for one implementation of the interface
from lexicon.providers.dnsmadeeasy import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsmadeeasyProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'dnsmadeeasy'
    domain = 'capsulecd.com'
    provider_opts = {'api_endpoint': 'http://api.sandbox.dnsmadeeasy.com/V2.0'}
    def _filter_headers(self):
        return ['x-dnsme-apiKey', 'x-dnsme-hmac', 'Authorization']
