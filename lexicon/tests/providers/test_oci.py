# coding: utf-8
# Copyright (c) 2016, Jason Kulatunga
# Copyright (c) 2021, Oracle and/or its affiliates.
import re
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class OciProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for OCI provider"""

    provider_name = "oci"
    domain = "lexicon-test.com"

    # Provide a fake credentials but the same region as the recorded tests
    def _test_parameters_overrides(self):
        return {
            "auth_user": "ocid1.user.oc1..aaaaaaa",
            "auth_tenancy": "ocid1.tenancy.oc1..aaaaaaaa",
            "auth_fingerprint": "aa:11:bb:22:cc:33:dd:44:ee:55:ff:66:a1:77:a2:88",
            "auth_region": "us-ashburn-1",
            "auth_key_content": """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA17lz4CMII+rpvu9Pi/AkOosjQR+kvDxdpbbxYY2JMkRnTuuN
nb7kefWQ9fEqsmTJcaUl0rrDORrYU+W+WYmuPYh839BeKPFbg/WbfPFMhLwF2X6G
w2Ozj7a9JceEYsuOptxtYawYabsN3wbPLAuTvY4B08kGLgVIzs7A3L/6JPbHJhjV
YuiRwWe2zzD64ERe3UuGEOXcTyU/guS3bX91W46E4vw6CFL2GiNgI5Q46xF3D31/
P/GKdFewm8rr7kAEouGW4mhOw0KI/mqgNrctQt+YQAzw/QKI4+umMu01ZtuYXRbF
40JsTuQOxnmClf7P59YrsI3ltBA94XthyVxh0QIDAQABAoIBADqnXt0zSTRS2+kh
MjSvP3p3eEdtriHMG/5BppHKpOH4/UnU+/VHAOI0JYzpXJ2Sj78JkyYfx5LQPL9a
+Q1pROnQIXvNMLzbGvHfJr6q8Q4p/UEsiMG5awoJOpZ6EAG4rPmrd0YWP7EHvfbE
6DFmmG3ynYaS4s5Ce5BXYNLkk8PWoWpEBGDOrdOU6bvMFqEgzqjnlbVNwGDP09HQ
fGtnycAqOsyC2CnrpNoOq6TWr/Y7s0EViajYxxTgoSgXnscntz8M2tqCW3Hd1T94
w2DOe1W5EGIkVrNpTePwFCkqPI47kTUT1eHDowf5NmRADJVDHr5H6yNCk7d/u2mr
6JsggE0CgYEA8YUBc/fagXLVAsEi3sOcyJrq04C+oy3Zz7zHz7ZH72cfJvaPlBPI
FPLVhEptn7bPMR7JuzUL6BckEnoPdXG52ncnZZbKMKXfBS6IkC/SSYjX6TWBXH9I
523QUi45N68UGb+opX/0iTvSrimK4wDWdz+Umx3rbt6uqmwuCHj9dn8CgYEA5KiG
7bnMRQAMadOOeFQePpViisEuHAAtL4f8qbXrwEjEjCjFBb3Hifdl6bRsvU8LEcN2
6YUM+KQXTOu+10N+4ANptjXzHJMIliO6FQ+7S8Rs/wDSrtuKHaEQR19HgyJzPfSi
ptZNWBFphrFE3nYO2GoYqCGwFYqNkW084XPBH68CgYEAyZcJBXEF0zK0FV576pA/
1zlndC5r8Owed8TMytUM6gia+fynDyQLx2CBU7CEG+GMwyU9oKLAU3KtSzbSnGbW
iEEYgzT/gueQZVTX6/Hehj5QaXmdhkU/5tvEHDQ00gOytWNCMxHAXKOwUGqgYKWc
XWCWe3rXvmzkQZ+WNMA4X6UCgYEAgJcmClsKvWMhmAIZhSIJQDjSiiXJwIV449oe
BXMBeclyf0AOTQRFSxmOfrewz2W8W+kI3pqsiMf/MosBcB3NJD3HHWmJpvApTAYb
h+yo8BsvENltolhke/UwKnMyzFR7asRBFIJATN698bmPeWv7PUmtRCBt3i9lHfvI
2SE34pECgYABPlBhx/irQMLXOacZxpXdVUj6/ivy4asiHe4OZN4uSXS1WqmrRHBe
Spzc4VkUFCDazQqxbG2/4ElGUzw+z0C0KMsSfSXTIk/YpNkyrCTwsllyvZrH7gVP
qpq9aJr7G9qW+9Yovwm2qLR1joa4XoOqn13bkEU7lc96fyRBr0ucDg==
-----END RSA PRIVATE KEY-----
""",
        }

    def _filter_headers(self):
        return ["authorization", "x-content-sha256"]

    def _filter_response(self, response):

        response["body"]["string"] = re.sub(
            br'"compartmentId":"[\w.-]+"',
            b'"compartmentId":"OCI-COMPARTMENT-ID"',
            response["body"]["string"],
        )
        response["body"]["string"] = re.sub(
            br'"id":"[\w.-]+"',
            b'"id":"DNS-ZONE-ID"',
            response["body"]["string"],
        )
        return response
