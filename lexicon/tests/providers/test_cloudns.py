"""Integration tests for CloudNS"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CloudnsProviderTests(TestCase, IntegrationTests):
    """TestCase for CloudNS"""
    provider_name = 'cloudns'
    domain = 'api-example.com'

    def _filter_query_parameters(self):
        return ['auth-id', 'sub-auth-id', 'sub-auth-user', 'auth-password']

    def _filter_post_data_parameters(self):
        return ['auth-id', 'sub-auth-id', 'sub-auth-user', 'auth-password']
