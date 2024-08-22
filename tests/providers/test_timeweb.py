"""Integration tests for Timeweb"""
from unittest import TestCase

from integration_tests import IntegrationTestsV2

import pytest


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTestsV2
class TimewebProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Timeweb provider"""

    provider_name = 'timeweb'
    domain = 'example.com'

    def _filter_post_data_parameters(self):
        return ['login_token']

    def _filter_headers(self):
        return ['Authorization']

    def _filter_query_parameters(self):
        return ['secret_key']

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
        to filter the provider response."""
        return response

    @pytest.mark.skip(reason="provider only supports TXT records without delegation")
    def test_provider_when_calling_create_record_for_A_with_valid_name_and_content(self):
        return

    @pytest.mark.skip(reason="provider only supports TXT records without delegation")
    def test_provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(self):
        return

    @pytest.mark.skip(reason="provider does not support TTL")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return
