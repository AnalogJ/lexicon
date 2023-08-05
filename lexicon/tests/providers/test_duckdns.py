# Test for one implementation of the interface
from unittest import TestCase, mock

import pytest

from lexicon.providers.duckdns import Provider
from lexicon.tests.providers import integration_tests

try:
    import dns.resolver
except ImportError:
    pass


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class DuckdnsProviderTests(TestCase, integration_tests.IntegrationTestsV2):
    """Integration tests for Duck DNS"""

    provider_name = "duckdns"
    domain = "testlexicon.duckdns.org"

    def _filter_headers(self):
        return ["Location"]

    def _filter_query_parameters(self):
        return ["token"]

    # skip unsupported features
    @pytest.mark.skip(reason="The Duck DNS API does not support authentication")
    def test_provider_authenticate(self):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support authentication")
    def test_provider_authenticate_with_unmanaged_domain_should_fail(self):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support CNAME records")
    def test_provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(
        self,
    ):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support altering the TTL")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support record sets")
    def test_provider_when_calling_create_record_multiple_times_should_create_record_set(
        self,
    ):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support record sets")
    def test_provider_when_calling_list_records_should_handle_record_sets(self):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support record sets")
    def test_provider_when_calling_delete_record_with_record_set_name_remove_all(self):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support record sets")
    def test_provider_when_calling_delete_record_with_record_set_by_content_should_leave_others_untouched(
        self,
    ):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support multiple TXT records")
    def test_provider_when_calling_update_record_should_modify_record(self):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support multiple TXT records")
    def test_provider_when_calling_update_record_with_full_name_should_modify_record(
        self,
    ):
        return

    @pytest.mark.skip(reason="The Duck DNS API does not support multiple TXT records")
    def test_provider_when_calling_update_record_with_fqdn_name_should_modify_record(
        self,
    ):
        return

    # mock DNS queries
    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_create_record_with_duplicate_records_should_be_noop(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # list records, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
        ]
        super().test_provider_when_calling_create_record_with_duplicate_records_should_be_noop()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_list_records_with_no_arguments_should_list_all(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # list records, no A no AAAA no TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
        ]
        super().test_provider_when_calling_list_records_with_no_arguments_should_list_all()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_list_records_with_fqdn_name_filter_should_return_record(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # list records, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
        ]
        super().test_provider_when_calling_list_records_with_fqdn_name_filter_should_return_record()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_list_records_with_full_name_filter_should_return_record(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # list records, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
        ]
        super().test_provider_when_calling_list_records_with_full_name_filter_should_return_record()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_list_records_with_name_filter_should_return_record(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # list records, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
        ]
        super().test_provider_when_calling_list_records_with_name_filter_should_return_record()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # update record with a list, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
        ]
        super().test_provider_when_calling_update_record_should_modify_record_name_specified()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_delete_record_by_filter_should_remove_record(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # delete record with a list, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
            # list records after delete, no A no AAAA no TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
        ]
        super().test_provider_when_calling_delete_record_by_filter_should_remove_record()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # delete record with a list, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
            # list records after delete, no A no AAAA no TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
        ]
        super().test_provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # delete record with a list, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
            # list records after delete, no A no AAAA no TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
        ]
        super().test_provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_delete_record_by_identifier_should_remove_record(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = [
            # first list, no A no AAAA one TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.rrset.from_text(
                "testlexicon.duckdns.org", 60, "IN", "TXT", "challengetoken"
            ),
            # second list, no A no AAAA no TXT
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
            dns.resolver.NoAnswer,
        ]
        super().test_provider_when_calling_delete_record_by_identifier_should_remove_record()

    @mock.patch.object(Provider, "_get_dns_rrset")
    def test_provider_when_calling_list_records_with_invalid_filter_should_be_empty_list(
        self,
        mock_rrset,
    ):
        mock_rrset.side_effect = dns.resolver.NoAnswer
        super().test_provider_when_calling_list_records_with_invalid_filter_should_be_empty_list()

    # provider specific tests
    def test_duckdns_domain_logic(self):
        assert Provider._get_duckdns_domain("testlexicon") == "testlexicon"
        assert Provider._get_duckdns_domain("testlexicon.duckdns.org") == "testlexicon"
        assert (
            Provider._get_duckdns_domain("test.testlexicon.duckdns.org")
            == "testlexicon"
        )
        with pytest.raises(Exception):
            Provider._get_duckdns_domain("test.testlexicon")
