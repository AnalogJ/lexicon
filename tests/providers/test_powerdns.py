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
		options.update({'pdns_server':'https://dnsadmin.hhome.me','pdns_server_id':'localhost'})
		return options

	# TODO: this should be enabled
	@pytest.mark.skip(reason="regenerating auth keys required")
	def test_Provider_when_calling_update_record_should_modify_record_name_specified(self):
		return

	@pytest.mark.skip(reason="TODO: extended test suite, needs contributor to implement")
	def test_Provider_when_calling_list_records_with_invalid_filter_should_be_empty_list(self):
		return
	@pytest.mark.skip(reason="TODO: extended test suite, needs contributor to implement")
	def test_Provider_when_calling_list_records_should_handle_record_sets(self):
		return

	@pytest.mark.skip(reason="TODO: extended test suite, needs contributor to implement")
	def test_Provider_when_calling_delete_record_with_record_set_name_remove_all(self):
		return

	@pytest.mark.skip(reason="TODO: extended test suite, needs contributor to implement")
	def test_Provider_when_calling_delete_record_with_record_set_by_content_should_leave_others_untouched(self):
		return

	@pytest.mark.skip(reason="TODO: extended test suite, needs contributor to implement")
	def test_Provider_when_calling_create_record_with_duplicate_records_should_be_noop(self):
		return

	@pytest.mark.skip(reason="TODO: extended test suite, needs contributor to implement")
	def test_Provider_when_calling_create_record_multiple_times_should_create_record_set(self):
		return