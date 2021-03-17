"""Integration tests for PowerDNS"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class PowerdnsProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for PowerDNS"""

    provider_name = "powerdns"
    domain = "sometestdomain.com"

    def _filter_headers(self):
        return ["X-API-Key"]

    def _test_parameters_overrides(self):
        return {"pdns_server": "http://127.0.0.1:8081", "pdns_server_id": "localhost"}

    # TODO: enable the skipped tests
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        return
