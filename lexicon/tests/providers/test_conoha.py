"""Integration tests for Conoha"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class ConohaProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Conoha"""

    provider_name = "conoha"
    domain = "narusejun.com"

    def _test_parameters_overrides(self):
        return {"region": "tyo1"}

    def _test_fallback_fn(self):
        return lambda x: None if x in ("priority") else "placeholder_" + x

    def _filter_post_data_parameters(self):
        return ["auth"]

    def _filter_headers(self):
        return ["X-Auth-Token"]
