# Test for one implementation of the interface
from lexicon.providers.softlayer import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class SoftLayerProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'softlayer'
    domain = 'example.com'

    # SoftLayer does not provide a sandbox API; actual credentials are required
    # Keeping this here for when fixtures need to be regenerated
    #def _test_options(self):
    #    options = super(SoftLayerProviderTests, self)._test_options()
    #    options.update({
    #        'auth_username': 'foo',
    #        'auth_api_key': 'bar'
    #        })
    #    return options
