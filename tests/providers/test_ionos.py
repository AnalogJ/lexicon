"""Integration tests for IONOS"""

import json
import os
from unittest import TestCase

from integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTestsV2
class IONOSProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for IONOS provider"""

    provider_name = "ionos"
    domain = os.environ.get("LEXICON_IONOS_DOMAIN", "example.com")

    def _filter_request(self, request):
        request.uri = request.uri.replace(self.domain, "example.com")
        if request.body:
            body = request.body.decode("utf-8")
            body = body.replace(self.domain, "example.com")
            request.body = body.encode("utf-8")
        return request

    def _filter_headers(self):
        return ["x-api-key"]

    def _filter_response(self, response):
        for key in ["Set-Cookie", "x-b3-traceid"]:
            response["headers"].pop(key, None)
        body = response["body"]["string"].decode("utf-8")
        try:
            data = json.loads(body)
            if isinstance(data, list):
                data = [e for e in data if not self._is_unrelated_zone(e)]
                body = json.dumps(data)
        except json.JSONDecodeError:
            pass
        body = body.replace(self.domain, "example.com")
        response["body"]["string"] = body.encode("utf-8")
        return response

    def _is_unrelated_zone(self, entry):
        return (
            isinstance(entry, dict)
            and "name" in entry
            and not entry["name"].endswith(self.domain)
        )
