"""Integration tests for INWX"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


class InwxProviderTests(TestCase, IntegrationTests):
    """TestCase for INWX"""
    provider_name = 'inwx'
    domain = 'lexicon-testrunner.com'

    def _test_parameters_overrides(self):
        return {
            'endpoint': 'https://api.ote.domrobot.com/xmlrpc/'
        }
