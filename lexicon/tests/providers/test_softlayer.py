"""Integration tests for Softlayer"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class SoftLayerProviderTests(TestCase, IntegrationTests):
    """TestCase for SoftLayer"""
    provider_name = 'softlayer'
    domain = 'example.com'

    # SoftLayer does not provide a sandbox API; actual credentials are required
    # Keeping this here for when fixtures need to be regenerated
    # def _test_options(self):
    #    options = super(SoftLayerProviderTests, self)._test_options()
    #    options.update({
    #        'auth_username': 'foo',
    #        'auth_api_key': 'bar'
    #        })
    #    return options

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.fixture(autouse=True)
    def _skip_suite(self, request):  # pylint: disable=no-self-use
        if request.node.get_closest_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')
