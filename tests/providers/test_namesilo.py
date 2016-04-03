# Test for one implementation of the interface
from lexicon.providers.namesilo import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class NameSiloProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'namesilo'
    domain = 'capsulecdfake.com'
    provider_opts = {'api_endpoint': 'http://sandbox.namesilo.com/api'}
    def _filter_query_parameters(self):
        return ['key']
