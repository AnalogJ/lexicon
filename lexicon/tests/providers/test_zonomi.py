"""Integratoin tests for Zonomi"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV1


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
# TODO: migrate to IntegrationTestsV2 and its extended test suite
class ZonomiProviderTests(TestCase, IntegrationTestsV1):
    """TestCase for Zonomi"""

    provider_name = "zonomi"
    domain = "pcekper.com.ar"

    def _filter_query_parameters(self):
        return ["api_key"]

    # TODO: enable the skipped tests
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        return

    def _test_parameters_overrides(self):
        return {"auth_entrypoint": "zonomi"}
