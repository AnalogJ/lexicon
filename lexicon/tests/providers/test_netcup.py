"""Integration tests for netcup"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class NetcupProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for netcup."""

    provider_name = "netcup"
    domain = "coldfix.de"

    def _filter_post_data_parameters(self):
        # actually only param[customerid, apikey, apipassword, apisessionid],
        # but I don't think this method allows filtering nested keys...
        return ["param"]

    def _test_parameters_overrides(self):
        return {
            "api_endpoint": "https://ccp.netcup.net/run/webservice/servers/endpoint.php?JSON"
        }

    @pytest.mark.skip(reason="TTL can not be set via netcup API")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        pass
