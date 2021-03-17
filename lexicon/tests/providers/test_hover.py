"""Integration tests for Hover"""
import json
import re
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


class HoverProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Hover"""

    provider_name = "hover"
    domain = "novuslex.com"
    domain_id = "dom1127777"
    hoverauth = "0123456789abcdef0123456789abcdef"
    hover_session = "0123456789abcdef0123456789abcdef"

    def _filter_post_data_parameters(self):
        return ["username", "password"]

    def _filter_headers(self):
        return ["Cookie"]

    def _filter_query_parameters(self):
        return ["hover_session", "hoverauth"]

    def _replace_auth(self, cookie):
        cookie = re.sub(
            "hover_session=.*;", f"hover_session={self.hover_session};", cookie
        )
        cookie = re.sub("hoverauth=.*;", f"hoverauth={self.hoverauth};", cookie)
        return cookie

    def _filter_response(self, response):
        if "basestring" not in globals():
            basestring = str

        if "set-cookie" in response["headers"]:
            if isinstance(response["headers"]["set-cookie"], basestring):
                response["headers"]["set-cookie"] = self._replace_auth(
                    response["headers"]["set-cookie"]
                )
            else:
                for i, cookie in enumerate(response["headers"]["set-cookie"]):
                    response["headers"]["set-cookie"][i] = self._replace_auth(cookie)

        try:
            filtered_body = json.loads(response["body"]["string"].decode("UTF-8"))
        except ValueError:
            # Body is not json during authentication, so we let it through.
            # Helper function _request in hover.py will raise exception when
            # response is not json and it should be.
            pass
        else:
            # filter out my personal contact information
            if "contact" in filtered_body:
                del filtered_body["contact"]

            # if the response is listing all my domains then return a mock response
            if "domains" in filtered_body and len(filtered_body["domains"]) > 1:
                filtered_body["domains"] = [
                    {
                        "id": self.domain_id,
                        "domain_name": self.domain,
                        "status": "active",
                    }
                ]

            response["body"]["string"] = json.dumps(filtered_body).encode("UTF-8")
        return response
