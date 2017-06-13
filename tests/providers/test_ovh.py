# Test for one implementation of the interface
from lexicon.providers.ovh import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class OvhProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'ovh'
    domain = 'elogium.net'
    def _filter_post_data_parameters(self):
        return ['login_token']

    def _filter_headers(self):
        return ['Authorization']

    def _filter_query_parameters(self):
        return ['application_key', 'application_secret', 'consumer_key']
