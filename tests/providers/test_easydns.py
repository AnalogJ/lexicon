# Test for one implementation of the interface
from lexicon.providers.easydns import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class EasyDnsProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'easydns'
    domain = 'easydnstemp.com'
    provider_opts = {'api_endpoint': 'http://sandbox.rest.easydns.net'}
    def _filter_headers(self):
        return ['Authorization']
    def _filter_query_parameters(self):
        return ['_key', '_user']
