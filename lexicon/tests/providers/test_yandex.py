"""Integration tests for Yandex PDD"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class YandexPDDProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Yandex PDD"""

    provider_name = "yandex"
    domain = "example.com"

    def _filter_headers(self):
        """Sensitive headers to be filtered."""
        return ["Authorization", "PddToken"]

    # filter out data which change on each run
    def _filter_response(self, response):
        if "X-Request-Id" in response["headers"]:
            del response["headers"]["X-Request-Id"]
        if "X-qloud-router" in response["headers"]:
            del response["headers"]["X-qloud-router"]
        return response
