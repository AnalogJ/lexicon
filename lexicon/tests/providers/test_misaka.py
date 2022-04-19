"""Integration tests for Misaka.IO"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class MisakaProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Misaka.IO"""

    provider_name = "misaka"
    domain = "misaka-dns-test.stream"

    def _filter_headers(self):
        return [
            "Authorization", "Set-Cookie",
            "X-Misaka-Debug", "X-Request-Id", "X-Served-By", "CF-RAY", "cf-request-id",
        ]
