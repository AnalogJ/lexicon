# Test for one implementation of the interface
from lexicon.providers.dnspod import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsParkProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'dnspod'
    domain = 'capsulecd.com'
    def _filter_post_data_parameters(self):
        return ['login_token']

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.fixture(autouse=True)
    def skip_suite(self, request):
        if request.node.get_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')