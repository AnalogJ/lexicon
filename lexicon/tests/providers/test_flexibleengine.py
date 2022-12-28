"""Integration tests for DigitalOcean"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests

# No tests for this provider, no domain for test

class FlexibleEngineProviderTests(IntegrationTestsV2):
    """TestCase for FlexibleEngine"""

    provider_name = "flexibleengine"
    # domain = "flexibleengine.test"

    def _filter_headers(self):
        return ["X-Auth-Token"]
    
    def _test_fallback_fn(self):
        return (
            lambda x: "placeholder_" + x
            if x not in ("zone_id")
            else ""
        )