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


    def _test_engine_overrides(self):
        overrides = super(EasyDnsProviderTests, self)._test_engine_overrides()
        overrides.update({'api_endpoint': 'http://sandbox.rest.easydns.net'})
        return overrides

    def _filter_headers(self):
        return ['Authorization']
    def _filter_query_parameters(self):
        return ['_key', '_user']

    # TODO: this should be enabled
    @pytest.mark.skip(reason="regenerating auth keys required")
    def test_Provider_when_calling_update_record_should_modify_record_name_specified(self):
        return