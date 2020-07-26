"""Integration tests for nsone"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class Ns1ProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for nsone"""

    provider_name = "nsone"
    domain = "lexicon-example.com"

    def _filter_headers(self):
        return ["X-NSONE-Key", "Authorization"]

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return

    # TODO: enable the skipped tests
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        return
