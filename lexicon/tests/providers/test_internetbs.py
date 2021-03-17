"""Integration tests for InternetBS"""
import os
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class InternetbsProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for InternetBS"""

    provider_name = "internetbs"
    domain = "world-of-ysera.com"

    def _filter_query_parameters(self):
        return ["ApiKey", "Password"]

    def _test_parameters_overrides(self):
        # workaround ENV problems during testing
        env_key = os.environ.get("LEXICON_INTERNETBS_AUTH_KEY")
        env_password = os.environ.get("LEXICON_INTERNETBS_AUTH_PASSWORD")
        return {"auth_key": env_key, "auth_password": env_password}
