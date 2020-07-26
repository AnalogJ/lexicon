"""Integration tests for Namesilo"""
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class NameSiloProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Namesilo"""

    provider_name = "namesilo"
    domain = "capsulecdfake.com"

    def _filter_query_parameters(self):
        return ["key"]

    def _test_parameters_overrides(self):
        return {"api_endpoint": "http://sandbox.namesilo.com/api"}

    # TODO: enable the skipped tests
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        return
