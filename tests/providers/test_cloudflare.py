# Test for one implementation of the interface
from lexicon.providers.cloudflare import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CloudflareProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'cloudflare'
    domain = 'capsulecd.com'
    def _filter_headers(self):
        return ['X-Auth-Email', 'X-Auth-Key','set-cookie']

    @pytest.mark.skip(reason="new test, missing recording")
    def test_Provider_when_calling_update_record_should_modify_record_name_specified(self):
        return

    def _test_parameters_overrides(self):
        return {'api_endpoint': 'https://api.cloudflare.com/client/v4'}
