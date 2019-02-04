"""Integration tests for Subreg"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class SubregProviderTests(TestCase, IntegrationTests):
    """TestCase for Subreg"""
    provider_name = 'subreg'
    domain = 'oldium.xyz'
