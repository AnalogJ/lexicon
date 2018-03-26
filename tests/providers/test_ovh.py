# Test for one implementation of the interface
from unittest import TestCase
from lexicon.providers.ovh import Provider
from integration_tests import IntegrationTests
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class OvhProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'ovh'
    domain = 'elogium.net'

    def _filter_headers(self):
        return ['X-Ovh-Application', 'X-Ovh-Consumer', 'X-Ovh-Signature']

    # Override _test_options to call env_auth_options and then import auth config from env variables
    def _test_options(self):
        cmd_options = super(OvhProviderTests, self)._test_options()
        cmd_options.update({'auth_entrypoint':'ovh-eu'})
        return cmd_options

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