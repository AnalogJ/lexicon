# Test for one implementation of the interface
from lexicon.providers.gandi import Provider
from lexicon.common.options_handler import env_auth_options
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class GandiRPCProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'gandi'
    domain = 'reachlike.ca'
    provider_variant = 'RPC'

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_Provider_when_calling_list_records_after_setting_ttl(self):
        return

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.fixture(autouse=True)
    def skip_suite(self, request):
        if request.node.get_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')