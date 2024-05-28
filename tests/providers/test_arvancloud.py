"""Integration tests for Arvancloud.ir"""

from unittest import TestCase

from integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class ArvancloudProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Arvancloud.ir"""

    provider_name = "arvancloud"
    domain = "wkmag.ir"

    def _filter_headers(self):
        return ["Authorization"]
