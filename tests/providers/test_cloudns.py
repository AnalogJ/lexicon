# Test for one implementation of the interface
from unittest import TestCase

import pytest
from integration_tests import IntegrationTests
from lexicon.providers.cloudns import Provider


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CloudnsProviderTests(TestCase, IntegrationTests):
    Provider = Provider
    provider_name = 'cloudns'
    domain = 'api-example.com'

    def _filter_query_parameters(self):
        return ['auth-id', 'sub-auth-id', 'sub-auth-user', 'auth-password']

    def _filter_post_data_parameters(self):
        return ['auth-id', 'sub-auth-id', 'sub-auth-user', 'auth-password']
