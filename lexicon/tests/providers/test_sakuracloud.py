"""Integration tests for SakuraCloud"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV1


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
# TODO: migrate to IntegrationTestsV2 and its extended test suite
class SakruaCloudProviderTests(TestCase, IntegrationTestsV1):
    """TestCase for SakuraCloud"""

    provider_name = "sakuracloud"
    domain = "example.com"

    def _filter_headers(self):
        return ["Authorization"]

    # TODO: enable the skipped tests
    @pytest.mark.skip(reason="record id is not exists")
    def test_provider_when_calling_delete_record_by_identifier_should_remove_record(
        self,
    ):
        return
