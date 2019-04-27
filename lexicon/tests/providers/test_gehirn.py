"""Integration tests for Gehirn"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class GehirnProviderTests(TestCase, IntegrationTests):
    """TestCase for Gehirn"""
    provider_name = 'gehirn'
    domain = 'example.com'

    def _filter_headers(self):
        return ['Authorization']

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.fixture(autouse=True)
    def _skip_suite(self, request):  # pylint: disable=no-self-use
        if request.node.get_closest_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')
