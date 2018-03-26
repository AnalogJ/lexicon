# Test for one implementation of the interface
from lexicon.providers.sakuracloud import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class SakruaCloudProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'sakuracloud'
    domain = 'example.com'
    def _filter_headers(self):
        return ['Authorization']

    # TODO: this should be enabled
    @pytest.mark.skip(reason="record id is not exists")
    def test_Provider_when_calling_delete_record_by_identifier_should_remove_record(self):
        return

    @pytest.fixture(autouse=True)
    def skip_suite(self, request):
        if request.node.get_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')