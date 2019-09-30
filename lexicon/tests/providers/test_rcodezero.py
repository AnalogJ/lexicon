"""Integration tests for RcodeZero"""
from unittest import TestCase
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class RcodezeroProviderTests(TestCase, IntegrationTests):
    """TestCase for RcodeZero"""
    provider_name = 'rcodezero'
    domain = 'lexicon-test.at'

    def _filter_headers(self):
        return ['Authorization']
