"""Integration tests for FlexibleEngine Cloud"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests

class FlexibleEngineProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for FlexibleEngine"""

    provider_name = "flexibleengine"
    domain = "flexibleengine.test"

    def _filter_headers(self):
        return ["X-Auth-Token"]
    
    def _test_fallback_fn(self):
        return (
            lambda x: "placeholder_" + x
            if x not in ("auth_token","zone_id")
            else ""
        )
    
    @pytest.mark.skip(reason="Content returned is an Array not a String")
    def test_provider_when_calling_list_records_with_fqdn_name_filter_should_return_record(
        self,
    ):
        return

    @pytest.mark.skip(reason="Content returned is an Array not a String")
    def test_provider_when_calling_list_records_with_full_name_filter_should_return_record(
        self,
    ):
        return

    @pytest.mark.skip(reason="Content returned is an Array not a String")
    def test_provider_when_calling_list_records_with_name_filter_should_return_record(
        self,
    ):
        return

    @pytest.mark.skip(reason="Creating Multiple records matching type and name is not accepted by FlexibleEngine DNS Provider")
    def test_provider_when_calling_list_records_should_handle_record_sets(
        self,
    ):
        return

    @pytest.mark.skip(reason="Creating Multiple records matching type and name is not accepted by FlexibleEngine DNS Provider")
    def test_provider_when_calling_delete_record_with_record_set_by_content_should_leave_others_untouched(
        self,
    ):
        return