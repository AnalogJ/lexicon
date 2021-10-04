"""Integration tests for Transip"""
import os
from tempfile import mkstemp
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2

FAKE_KEY = b"""
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxV08IlJRwNq9WyyGO2xRyT0F6XIBD2R5CrwJoP7gIHVU/Mhk
KeK8//+MbUZtKFoeJi9lI8Cbkqe7GVk9yab6R2/vVzV21XRh+57R79nEh+QTf/vZ
dg+DjUn62U4lcgoVp3sHddIi/Zi58xz2a2lGGIdolsv1x0/PmAQPULt721IG/osp
RBjTtaZ8niXrOTfjH814i8kgXu74CCGu0X6kJBIezMA2wqY1ZKZYRMpfrxkEZe0t
45pEM1CmSTCqyDMpwYou9wJaDHn0ts1KvKkKBfmO4B0nqfW9Sv9rkmpBCLTtMobj
dQ8EwWv1L1g9uddkPALgRODEpR4fq7PTmq2VEQIDAQABAoIBAFf4wwEZaE9qMNUe
94YtNhdZF/WCV26g/kMGpdQZR5WwNv2l5N+2rT/+jH140tcVtDKZFZ/mDnJESWV3
Hc9wmkaVYj2hGyLyCWq61CDxFGTuCLMXc0roh17HBwUtjAtU62oHsL+XtvkKxnfT
BRPDjPcKBFiS+S6qKII97QWzS/XpxL47VpXcYboVunzUncIKghC93LdvPp3ukh6x
HIarqyctqkksLJtLgH5ffuABCJLChetpOIfcfspjtMoji43CXXd7Y3rGWy3EzSHA
s4mNb4K6r8MOlJj3HiTn9bEgL2V2q3OHSYHYXexir67vkQeN+NsC80G0uODt6Uuo
Cd1RobECgYEA+O+nZYRc22jI8oqRoQeCx6cTWJoaf4OYDXcaerRMIiE7yigHNgmX
LGs9RYTVrWXzjM5KHVvPvavpm/zIBoa5fA7uqdH9BjuZVLm1COXzKxF5hevZuAxr
zGQWDbdvzdsihPBvwlf0dKScA/WIRW0KCqUmC6IlS/An4Y0nI05P+KsCgYEAyvby
cfUPgeanBnYE3GGou3cLiurzvK3vHuQl6vVE3DcheUj/5tKTwG5Q3/7y51MKHnfH
xEc/X2IePXYVy0JwpC6NHzkyJPuJ1zYlkQGSs81TUbYOk9SKi3SL9bM+3vRzYFoL
GMLJuvEqIscxLNqR0xQB5eBkg8T+AVJiA7cTITMCgYEAn5/ND2OYx3ihoiUIzOEs
EyonVaE7bJjNX5UH/bavOxNka3TPau8raOg7GeDbw5ykV53QGJNO2qjp24R0Hvs0
5UAN+gcU4HJHF/UdCN+q1esWqbFaopIUbbOgEJuXrcDembAzecM8la8X+9Ht19bb
oYfUpZELqW4NpKwGdLU6wpECgYAfn3hI3xjKcYiGji7Vs3WZt8OZol/VfvgpxPxP
bmWLNh/GCOSuLxMMQWPicpOgDSUfeCQs5bjvAJebleFxaOmp+wLL4Zp5fqOMX4hc
3nTgBNa9fXMp/0ySy9besk3SaR3s3jqqYfcSZG7fOk/kIC3mSFC/Y0Xl7fRxekeB
Mq4NVwKBgQDQ+3+cgZph5geq0PUuKMvMECDuCEnG8rrr4jTCe+sRP34y1IaxJ2w6
S6p+kvTBePSqV2wWZCls6p7mhGEto+8H9b4pWdmSqccn0vFu4kekm/OU4+IxqzWQ
KPeh76yhdzsFwzh+0LBPfkFgFn3YlHp0eoywNpm57MFxWx8u3U2Hkw==
-----END RSA PRIVATE KEY-----
"""


# The following fields were removed from the test fixtures:
#   getInfo: contacts, authcode, registrationDate, renewalDate
# using:
#   find tests/fixtures/cassettes/transip/
#       -name \*.json -exec sed -i 's/<contacts.*<\/contacts>//g' '{}' \;
#   find tests/fixtures/cassettes/transip/
#       -name \*.json -exec sed -i 's/<authCode.*<\/authCode>//g' '{}' \;
#   find tests/fixtures/cassettes/transip/
#       -name \*.json -exec sed -i 's/<registrationDate.*<\/registrationDate>//g' '{}' \;
#   find tests/fixtures/cassettes/transip/
#       -name \*.json -exec sed -i 's/<renewalDate.*<\/renewalDate>//g' '{}' \;


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
@pytest.mark.skip(
    reason="TransIP SOAP API is deprecated and cannot be maintained anymore."
)
class TransipProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Transip"""

    provider_name = "transip"
    domain = "hurrdurr.nl"

    # Disable setUp and tearDown, and set a real username and key in
    # provider_opts to execute real calls
    def _test_parameters_overrides(self):
        (_fake_fd, _fake_key) = mkstemp()
        _fake_file = os.fdopen(_fake_fd, "wb", 1024)
        _fake_file.write(FAKE_KEY)
        _fake_file.close()
        self._fake_key = _fake_key

        options = {"auth_username": "foo", "auth_api_key": _fake_key}

        return options

    def tearDown(self):
        try:
            os.unlink(self._fake_key)
        except AttributeError:
            # Method _test_options may not have been executed,
            # in this case self._fake_key does not exist.
            pass

    def _filter_headers(self):
        return ["Cookie"]

    @pytest.mark.skip(reason="manipulating records by id is not supported")
    def test_provider_when_calling_delete_record_by_identifier_should_remove_record(
        self,
    ):
        return

    @pytest.mark.skip(
        reason=(
            "adding docs.example.com as a CNAME target will result in a RFC 1035 error"
        )
    )
    def test_provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(
        self,
    ):
        return
