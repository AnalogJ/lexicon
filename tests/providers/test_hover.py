"""Integration tests for Hover"""
import json
import re
from unittest import TestCase

import pyotp

from integration_tests import IntegrationTestsV2


_FAKE_DOMAIN_ID = "dom1127777"
_FAKE_HOVERAUTH = "0123456789abcdef0123456789abcdef"
_FAKE_HOVER_SESSION = "0123456789abcdef0123456789abcdef"
_FAKE_TOTP_SECRET = pyotp.random_base32()


class HoverProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Hover"""

    provider_name = "hover"
    domain = "sudrien.work"

    def _filter_post_data_parameters(self):
        return ["username", "password", "code"]

    def _filter_headers(self):
        return ["Cookie"]

    def _filter_query_parameters(self):
        return ["hover_session", "hoverauth"]

    def _test_parameters_overrides(self):
        return {'auth_totp_secret': _FAKE_TOTP_SECRET}

    def _replace_auth(self, cookie):
        cookie = re.sub(
            "hover_session=.*;", f"hover_session={_FAKE_HOVER_SESSION};", cookie
        )
        cookie = re.sub("hoverauth=.*;", f"hoverauth={_FAKE_HOVERAUTH};", cookie)
        return cookie

    def _filter_response(self, response):
        if "set-cookie" in response["headers"]:
            if isinstance(response["headers"]["set-cookie"], str):
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
                        "id": _FAKE_DOMAIN_ID,
                        "domain_name": self.domain,
                        "status": "active",
                    }
                ]

            response["body"]["string"] = json.dumps(filtered_body).encode("UTF-8")
        return response
