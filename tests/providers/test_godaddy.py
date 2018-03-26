# Test for one implementation of the interface
from unittest import TestCase
from lexicon.providers.godaddy import Provider
from integration_tests import IntegrationTests

import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class GoDaddyProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'godaddy'
    # Domain existing in the GoDaddy OTE server at the time of the test (17/06/2017)
    domain = '000.biz'

    def _filter_headers(self):
        return ['Authorization']

    def _test_engine_overrides(self):
        overrides = super(GoDaddyProviderTests, self)._test_engine_overrides()
        # Use the OTE server, which allows tests without account
        overrides.update({'api_endpoint': 'https://api.ote-godaddy.com/v1'})
        return overrides

    def _test_options(self):
        cmd_options = super(GoDaddyProviderTests, self)._test_options()
        # This token is public,
        #   and used on https://developer.godaddy.com to test against OTE server
        cmd_options.update({
            'auth_key': 'UzQxLikm_46KxDFnbjN7cQjmw6wocia',
            'auth_secret': '46L26ydpkwMaKZV6uVdDWe'
            })
        return cmd_options

    @pytest.mark.skip(reason="GoDaddy does not use id in their DNS records")
    def test_Provider_when_calling_delete_record_by_identifier_should_remove_record(self):
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