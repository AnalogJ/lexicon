"""Integration tests for Cloudflare"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CloudflareProviderTests(TestCase, IntegrationTests):
    """TestCase for Cloudflare"""
    provider_name = 'cloudflare'
    domain = 'capsulecd.com'

    def _filter_headers(self):
        return ['X-Auth-Email', 'X-Auth-Key', 'set-cookie']

    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(self):
        return
