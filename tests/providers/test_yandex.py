# Test for one implementation of the interface
from lexicon.providers.yandex import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class YandexPDDProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'yandex'
    domain = 'example.com'
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_authenticate(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_authenticate_with_unmanaged_domain_should_fail(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_create_record_for_A_with_valid_name_and_content(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_create_record_for_TXT_with_fqdn_name_and_content(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_create_record_for_TXT_with_full_name_and_content(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_create_record_for_TXT_with_valid_name_and_content(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_delete_record_by_filter_should_remove_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_delete_record_by_identifier_should_remove_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_list_records_after_setting_ttl(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_list_records_with_fqdn_name_filter_should_return_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_list_records_with_full_name_filter_should_return_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_list_records_with_name_filter_should_return_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_list_records_with_no_arguments_should_list_all(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_update_record_should_modify_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_update_record_with_fqdn_name_should_modify_record(self):
        return
    @pytest.mark.skip(reason="Yandex PDD don't have public test API")
    def test_Provider_when_calling_update_record_with_full_name_should_modify_record(self):
        return
