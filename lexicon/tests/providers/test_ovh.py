"""Integration tests for OVH"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class OvhProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for OVH"""

    provider_name = "ovh"
    domain = "pacalis.net"

    def _filter_headers(self):
        return ["X-Ovh-Application", "X-Ovh-Consumer", "X-Ovh-Signature"]

    def _test_parameters_overrides(self):
        return {"auth_entrypoint": "ovh-eu"}
