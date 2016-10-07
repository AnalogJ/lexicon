"""Test for route53 implementation of the interface."""
import unittest
import os
from test.test_support import EnvironmentVarGuard
from lexicon.providers.route53 import Provider
from integration_tests import IntegrationTests


class Route53ProviderTests(unittest.TestCase, IntegrationTests):
    """Route53 Proivder Tests."""

    Provider = Provider
    provider_name = 'route53'
    domain = 'capsulecd.com'

    def _filter_headers(self):
        """Sensitive headers to be filtered."""
        return []

if __name__ == '__main__':
    unittest.main()
