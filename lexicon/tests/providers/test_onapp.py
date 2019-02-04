"""Integration tests for Onapp"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


class OnappProviderTests(TestCase, IntegrationTests):
    """TestCase for Oneapp"""
    provider_name = 'onapp'
    domain = 'my-test.org'

    def _filter_headers(self):
        return ['Authorization']

    def _test_parameters_overrides(self):
        return {'auth_server': 'https://dashboard.dynomesh.com.au'}
