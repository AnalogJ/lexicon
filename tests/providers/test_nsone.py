# Test for one implementation of the interface
from lexicon.providers.nsone import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class Ns1ProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'nsone'
    domain = 'capsulecd.com'
    def _filter_headers(self):
        return ['X-NSONE-Key', 'Authorization']

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_Provider_when_calling_list_records_after_setting_ttl(self):
        return