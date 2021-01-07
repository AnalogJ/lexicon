"""Integration tests for LuaDNS"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class LuaDNSProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for LuaDNS"""

    provider_name = "luadns"
    domain = "capsulecd.com"

    def _filter_headers(self):
        return ["Authorization"]

    @pytest.mark.skip(reason="CNAME requires FQDN for this provider")
    def test_provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(
        self,
    ):
        return

    # TODO: enable the skipped tests
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        return
