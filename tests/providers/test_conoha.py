# Test for one implementation of the interface
from lexicon.providers.conoha import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class ConohaProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'conoha'
    domain = 'narusejun.com'

    def _test_engine_overrides(self):
        overrides = super(ConohaProviderTests, self)._test_engine_overrides()
        overrides['fallbackFn'] = (lambda x: 'placeholder_' + x if x != 'priority' else '')
        return overrides

    def _filter_post_data_parameters(self):
        return ['auth']

    def _filter_headers(self):
        return ['X-Auth-Token']
