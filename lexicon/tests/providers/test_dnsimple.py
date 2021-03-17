"""Integration tests for DNSSimple"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsimpleProviderTests(TestCase, IntegrationTests):
    """TestCase for DNSSimple"""
    provider_name = 'dnsimple'
    domain = 'lexicontest.us'

    def _test_parameters_overrides(self):
        return {
            'api_endpoint': 'https://api.sandbox.dnsimple.com/v2',
            'region': 'global'
        }

    def _filter_headers(self):
        return ['Authorization', 'set-cookie', 'X-Dnsimple-OTP']
