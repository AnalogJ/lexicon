"""Integration tests for SakuraCloud"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class SakruaCloudProviderTests(TestCase, IntegrationTests):
    """TestCase for SakuraCloud"""
    provider_name = 'sakuracloud'
    domain = 'example.com'

    def _filter_headers(self):
        return ['Authorization']

    # TODO: this should be enabled
    @pytest.mark.skip(reason="record id is not exists")
    def test_provider_when_calling_delete_record_by_identifier_should_remove_record(self):
        return

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.fixture(autouse=True)
    def _skip_suite(self, request):  # pylint: disable=no-self-use
        if request.node.get_closest_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')
