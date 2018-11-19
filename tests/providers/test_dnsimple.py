# Test for one implementation of the interface
from unittest import TestCase

import pytest
from integration_tests import IntegrationTests
from lexicon.providers.dnsimple import Provider


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests


class DnsimpleProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'dnsimple'
    domain = 'lexicontest.us'

    def _test_parameters_overrides(self):
        return {
            'api_endpoint': 'https://api.sandbox.dnsimple.com/v2',
            'region': 'global'
        }

    def _filter_headers(self):
        return ['Authorization', 'set-cookie', 'X-Dnsimple-OTP']
