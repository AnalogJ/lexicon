"""Integration tests for Linode V4"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class Linode4ProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Linode V4"""

    provider_name = "linode4"
    domain = "lexicon-test.com"

    def _filter_post_data_parameters(self):
        return []

    def _filter_headers(self):
        return ["Authorization"]

    def _filter_query_parameters(self):
        return []

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return
