"""Integration tests for Joker.com provider"""
import re
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


class JokerProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Joker.com"""

    provider_name = "joker"
    domain = "erdtfrau.de"

    def _filter_query_parameters(self):
        return [
            ("api-key", "DUMMY_API_KEY"),
            ("auth-sid", "DUMMY_AUTH_SID"),
        ]

    def _filter_response(self, response):
        body = response["body"]["string"].decode("utf-8")
        body = re.sub(r"Auth-Sid: \w+\n", "Auth-Sid: DUMMY_AUTH_SID\n", body)
        response["body"]["string"] = body.encode("utf-8")

        return response
