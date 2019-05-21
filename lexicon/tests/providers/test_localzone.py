"""Integration tests for Localzone"""
import os
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTests

FILENAME = "db.example.com"
ZONEFILE = """
$ORIGIN example.com.     ; designates the start of this zone file in the namespace
$TTL 1h                  ; default expiration time of all resource records without their own TTL value
example.com.  IN  SOA   ns.example.com. username.example.com. ( 2007120710 1d 2h 4w 1h )
example.com.  IN  NS    ns                    ; ns.example.com is a nameserver for example.com
example.com.  IN  NS    ns.somewhere.example. ; ns.somewhere.example is a backup nameserver for example.com
example.com.  IN  MX    10 mail.example.com.  ; mail.example.com is the mailserver for example.com
@             IN  MX    20 mail2.example.com. ; equivalent to above line, "@" represents zone origin
@             IN  MX    50 mail3              ; equivalent to above line, but using a relative host name
example.com.  IN  A     192.0.2.1             ; IPv4 address for example.com
              IN  AAAA  2001:db8:10::1        ; IPv6 address for example.com
ns            IN  A     192.0.2.2             ; IPv4 address for ns.example.com
              IN  AAAA  2001:db8:10::2        ; IPv6 address for ns.example.com
www           IN  CNAME example.com.          ; www.example.com is an alias for example.com
wwwtest       IN  CNAME www                   ; wwwtest.example.com is another alias for www.example.com
mail          IN  A     192.0.2.3             ; IPv4 address for mail.example.com
mail2         IN  A     192.0.2.4             ; IPv4 address for mail2.example.com
mail3         IN  A     192.0.2.5             ; IPv4 address for mail3.example.com
@             IN  TXT   "v=spf1 mx ~all"      ; SPFv1 record for example.com
"""

@pytest.fixture(scope="module", autouse=True)
def testfile():
    """Create a local zone file for testing."""
    test_file = open(FILENAME, "w")
    test_file.write(ZONEFILE)
    test_file.close()
    yield
    os.remove(FILENAME)

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class LocalzoneProviderTests(TestCase, IntegrationTests):
    """Integration tests for Localzone"""
    provider_name = "localzone"
    domain = "example.com"

    def _test_parameters_overrides(self):
        options = {
            "filename": FILENAME
        }

        return options

    def _test_fallback_fn(self):
        return lambda _: None

    @pytest.mark.skip(reason="localzone does not require authentication")
    def test_provider_authenticate(self):
        return

    @pytest.mark.skip(reason="localzone does not require authentication")
    def test_provider_authenticate_with_unmanaged_domain_should_fail(self):
        return
