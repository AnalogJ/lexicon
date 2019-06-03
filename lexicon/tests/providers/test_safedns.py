# Test for one implementation of the interface
import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class SafednsProviderTests(TestCase, IntegrationTests):
	"""Integration tests for SafeDNS provider"""
	provider_name = 'safedns'
	domain = 'calv.tk'

	def _filter_headers(self):
		return ['Authorization']

	@pytest.mark.skip(reason="Records TTL are not supported by SafeDNS")
	def test_provider_when_calling_list_records_after_setting_ttl(self):
		return

	@pytest.mark.skip(reason="CNAME requires FQDN for this provider")
	def test_provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(self):
		return

	@pytest.mark.skip(reason="new test, missing recording")
	def test_provider_when_calling_update_record_should_modify_record_name_specified(self):
		return

	def _filter_response(self, response):
		"""See `IntegrationTests._filter_response` for more information on how
		to filter the provider response."""
		return response
