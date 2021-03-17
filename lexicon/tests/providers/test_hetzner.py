"""Integration tests for Hetzner"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class HetznerProviderTests(TestCase, IntegrationTests):
    """TestCase for Hetzner"""
    provider_name = 'hetzner'
    domain = 'softwarekollektiv.de'

    def _filter_headers(self):
        return ['Auth-API-Token']
