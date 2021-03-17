"""Test for one implementation of the interface"""
from unittest import TestCase
import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class SafednsProviderTests(TestCase, IntegrationTests):
    """Integration tests for SafeDNS provider"""
    provider_name = 'safedns'
    domain = 'lexicon.tests'

    def _filter_headers(self):
        return ['Authorization']

    @pytest.mark.skip(reason="Record-level TTLs are not supported by this provider")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return

    @pytest.mark.skip(reason="CNAME requires FQDN for this provider")
    def test_provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(self):
        return
