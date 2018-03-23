# Test for one implementation of the interface
from lexicon.providers.dnsimple import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsimpleProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'dnsimple'
    domain = 'lexicontest.com'

    def _test_engine_overrides(self):
        overrides = super(DnsimpleProviderTests, self)._test_engine_overrides()
        overrides.update({'api_endpoint': 'https://api.sandbox.dnsimple.com/v2'})
        return overrides

    # Override _test_options to call env_auth_options and then import auth config from env variables
    def _test_options(self):
        cmd_options = super(DnsimpleProviderTests, self)._test_options()
        cmd_options['regions'] = ['global']
        return cmd_options

    def _filter_headers(self):
        return ['Authorization','set-cookie','X-Dnsimple-OTP']

    # TODO: this should be enabled
    @pytest.mark.skip(reason="regenerating auth keys required")
    def test_Provider_when_calling_update_record_should_modify_record_name_specified(self):
        return