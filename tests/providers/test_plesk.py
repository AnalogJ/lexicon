# Test for one implementation of the interface
from lexicon.providers.plesk import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class PleskProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'plesk'
    domain = 'lexicon-test.com'

    def _filter_headers(self):
        return ['HTTP_AUTH_LOGIN', 'HTTP_AUTH_PASSWD']

    def _test_options(self):
        options = super(PleskProviderTests, self)._test_options()
        options.update({'plesk_server':'https://quasispace.de:8443'})
        return options

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_Provider_when_calling_list_records_after_setting_ttl(self):
        return
