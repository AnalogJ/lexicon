# Test for one implementation of the interface
from lexicon.providers.linode4 import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class Linode4ProviderTests(TestCase, IntegrationTests):

	Provider = Provider
	provider_name = 'linode4'
	domain = 'lexicon-test.com'
	def _filter_post_data_parameters(self):
		return []

	def _filter_headers(self):
		return ['Authorization']

	def _filter_query_parameters(self):
		return []

	def _ttl_valid(self):
		return 3600

	@pytest.mark.skip(reason="Linode does not return error")
	def test_Provider_when_calling_create_record_with_invalid_ttl_should_raise(self):
		pass

	@pytest.mark.skip(reason="Linode does not return error")
	def test_Provider_when_calling_update_record_with_invalid_ttl_should_raise(self):
		pass
