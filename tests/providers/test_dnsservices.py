"""Integration tests for DNS.services"""

import re
from unittest import TestCase

from integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DNSservicesProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for DNS.services"""

    provider_name = "dnsservices"
    domain = "astylos.dk"

    def _filter_headers(self):
        return [("Authorization", "Bearer TOKEN")]

    def _filter_post_data_parameters(self):
        return [("username", "USERNAME"), ("password", "PASSWORD")]

    def _filter_response(self, response):
        response["body"]["string"] = re.sub(
            b'"token":"[^"]+"', b'"token":"TOKEN"', response["body"]["string"]
        )
        response["body"]["string"] = re.sub(
            b'"refresh":"[^"]+"', b'"refresh":"REFRESH"', response["body"]["string"]
        )
        return response
