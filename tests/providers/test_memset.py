# Test for one implementation of the interface
from lexicon.providers.memset import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class MemsetProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'memset'
    domain = 'testzone.com'

    def _filter_headers(self):
        return ['Authorization']
