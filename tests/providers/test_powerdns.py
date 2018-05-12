from lexicon.providers.powerdns import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class PowerdnsProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'powerdns'
    domain = 'example.com'

    def _filter_headers(self):
        return ['X-API-Key']

    def _test_options(self):
        options = super(PowerdnsProviderTests, self)._test_options()
        options.update({'pdns_server': 'https://dnsadmin.hhome.me', 'pdns_server_id': 'localhost'})
        return options

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.fixture(autouse=True)
    def skip_suite(self, request):
        if request.node.get_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')
