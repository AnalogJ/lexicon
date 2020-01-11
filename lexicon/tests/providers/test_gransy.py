"""Integration tests for Gransy"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class GransyProviderTests(TestCase, IntegrationTests):
    """TestCase for Gransy"""
    provider_name = 'gransy'
    domain = 'oldium.xyz'
