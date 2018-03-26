from lexicon.providers.zonomi import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class ZonomiProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'zonomi'
    domain = 'pcekper.com.ar'
        
    def _test_engine_overrides(self):
        overrides = super(ZonomiProviderTests, self)._test_engine_overrides()
        overrides.update({'api_endpoint': 'https://zonomi.com/app'})
        return overrides
    
    def _filter_query_parameters(self):
        return ['api_key']
