# Test for one implementation of the interface
import re
from unittest import TestCase

from lexicon.tests.providers import integration_tests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class MythicBeastsProviderTests(TestCase, integration_tests.IntegrationTestsV2):
    """Integration tests for Mythic Beasts provider"""

    provider_name = "mythicbeasts"
    domain = "lexitus.co.uk"

    def _filter_post_data_parameters(self):
        return ["access_token"]

    def _filter_headers(self):
        return ["Authorization"]

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
        to filter the provider response."""

        if "string" in response["body"]:
            response["body"]["string"] = re.sub(
                br"\"access_token\":\"[\w-]+\"",
                b'"access_token": "DUMMY_TOKEN"',
                response["body"]["string"],
            )

        return response

    def _test_fallback_fn(self):
        return lambda x: "placeholder_" + x if x not in ("auth_token") else ""
