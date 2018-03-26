# Test for one implementation of the interface
from lexicon.providers.namecheap import Provider
from lexicon.common.options_handler import env_auth_options
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class NamecheapProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'namecheap'
    domain = 'lexicontest.com'

    def _filter_query_parameters(self):
        return ['ApiKey','UserName', 'ApiUser']

    def _test_options(self):
        options = super(NamecheapProviderTests, self)._test_options()
        options.update({'auth_sandbox':True})
        options.update({'auth_client_ip':'127.0.0.1'})
        options.update(env_auth_options(self.provider_name))
        return options

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_Provider_when_calling_list_records_after_setting_ttl(self):
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