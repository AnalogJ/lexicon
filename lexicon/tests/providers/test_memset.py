"""Integration tests for Memset"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class MemsetProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Memset"""

    provider_name = "memset"
    domain = "testzone.com"

    def _filter_headers(self):
        return ["Authorization"]

    # TODO: enable the skipped tests
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        return
