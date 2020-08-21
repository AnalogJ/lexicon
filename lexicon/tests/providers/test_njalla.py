"""Integration tests for Njalla provider"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests


class NjallaProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Njalla"""

    provider_name = "njalla"
    domain = "example.com"

    def _filter_headers(self):
        return ["Authorization"]

    @pytest.mark.skip(reason="provider allows duplicate records")
    def test_provider_when_calling_create_record_with_duplicate_records_should_be_noop(
        self,
    ):
        return

    @pytest.mark.skip(reason="provider does not recognize record sets")
    def test_provider_when_calling_delete_record_with_record_set_name_remove_all(self):
        return
