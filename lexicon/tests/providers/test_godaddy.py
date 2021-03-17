"""Integration tests for Goddady"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class GoDaddyProviderTests(TestCase, IntegrationTests):
    """TestCase for Godaddy"""
    provider_name = 'godaddy'
    domain = 'fullm3tal.online'

    def _filter_headers(self):
        return ['Authorization']
