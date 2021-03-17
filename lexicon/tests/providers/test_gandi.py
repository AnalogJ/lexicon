"""Integration tests for Gandi"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class GandiRPCProviderTests(TestCase, IntegrationTests):
    """TestCase for Gandi on RPC"""
    provider_name = 'gandi'
    domain = 'reachlike.ca'
    provider_variant = 'RPC'

    def _test_parameters_overrides(self):
        return {'api_protocol': 'rpc'}


class GandiRESTProviderTests(TestCase, IntegrationTests):
    """TestCase for Gandi on REST API"""
    provider_name = 'gandi'
    domain = 't18s.fr'
    provider_variant = 'REST'

    def _filter_headers(self):
        return ['X-Api-Key']

    def _test_parameters_overrides(self):
        return {'api_protocol': 'rest'}
