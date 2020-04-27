"""Integration tests for Njalla provider"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests

class NjallaProviderTests(TestCase, IntegrationTests):
    """TestCase for Njalla"""
    provider_name = 'njalla'
    domain = 'example.com'

    def _filter_headers(self):
        return ['Authorization']

    @pytest.fixture(autouse=True)
    def _skip_suite(self, request):  # pylint: disable=no-self-use
        if request.node.get_closest_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')
