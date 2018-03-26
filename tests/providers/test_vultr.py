# Test for one implementation of the interface
from lexicon.providers.vultr import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class VultrProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'vultr'
    domain = 'capsulecd.com'
    def _filter_headers(self):
        return ['API-Key']

    # TODO: this should be enabled
    @pytest.mark.skip(reason="regenerating auth keys required")
    def test_Provider_when_calling_update_record_should_modify_record_name_specified(self):
        return

    @pytest.fixture(autouse=True)
    def skip_suite(self, request):
        if request.node.get_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')