"""Integration tests for DNSMadeEasy"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsmadeeasyProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for DNSMadeEasy"""

    provider_name = "dnsmadeeasy"
    domain = "capsulecd.com"

    def _test_parameters_overrides(self):
        return {"api_endpoint": "http://api.sandbox.dnsmadeeasy.com/V2.0"}

    def _filter_headers(self):
        return ["x-dnsme-apiKey", "x-dnsme-hmac", "Authorization"]

    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        return
