"""Integration tests for Softlayer"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV1


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
# TODO: migrate to IntegrationTestsV2 and its extended test suite
class SoftLayerProviderTests(TestCase, IntegrationTestsV1):
    """TestCase for SoftLayer"""

    provider_name = "softlayer"
    domain = "example.com"

    # SoftLayer does not provide a sandbox API; actual credentials are required
    # Keeping this here for when fixtures need to be regenerated
    # def _test_options(self):
    #    options = super(SoftLayerProviderTests, self)._test_options()
    #    options.update({
    #        'auth_username': 'foo',
    #        'auth_api_key': 'bar'
    #        })
    #    return options
