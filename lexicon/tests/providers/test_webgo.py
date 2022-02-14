"""Integration tests for Webgo"""
import re
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class WebgoProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Webgo"""

    provider_name = "webgo"
    domain = "klugscheissmodus.de"

    def _filter_post_data_parameters(self):
        return ["data%5BUser%5D%5Busername%5D", "data%5BUser%5D%5Bpassword%5D"]

    def _filter_headers(self):
        return ["Authorization", "Cookie"]

    def _filter_query_parameters(self):
        return ["pass"]

    def _filter_response(self, response):
        body = response["body"]["string"].decode("utf-8")
        # Filter out all Customer/Service IDs from Response
        body = re.sub(r"\b(16)([0-9]{3})\b", "XXXXX", body)
        # Filter out Clearname from Response
        body = re.sub(
            r"<div class=\"welcome\">.*?<\/div>",
            '<div class="welcome">John Doe</div>',
            body,
        )
        # Filter out all Domains not tested
        body = re.sub(
            r"<\s*td[^>]*>(?!("
            + re.escape(self.domain)
            + r"))(.[A-Za-z0-9]*\.[a-z]{2,3})<\s*/\s*td>",
            "<td>filtereddomain.de</td>",
            body,
        )
        response["body"]["string"] = body.encode("utf-8")
        return response
