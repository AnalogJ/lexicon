"""Integration tests for Plesk"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class PleskProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Plesk"""

    provider_name = "plesk"
    domain = "lexicon-test.com"

    def _filter_headers(self):
        return ["HTTP_AUTH_LOGIN", "HTTP_AUTH_PASSWD"]

    def _test_parameters_overrides(self):
        return {"plesk_server": "https://quasispace.de:8443"}

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return
