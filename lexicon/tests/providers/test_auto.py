"""Integration tests for auto"""
import socket
from unittest import TestCase, mock

import pytest

from lexicon.providers.auto import _get_ns_records_domains_for_domain
from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# This fixture ensures to mock _get_ns_records_domains_for_domain, in order to not rely
# on the machine on which the test is done, as this function call nslookup.
# Then it will prevent errors where there is no network or tested domain do not exists anymore.
@pytest.fixture(autouse=True)
def _nslookup_mock(request):
    if request.node.name == "test_nslookup_resolution":
        # Do not mock for the test that specifically test nslookup resolution.
        yield
    else:
        with mock.patch(
            "lexicon.providers.auto._get_ns_records_for_domain",
            return_value=["ns.ovh.net"],
        ) as fixture:
            yield fixture


# Guys, are we online ?
def _there_is_no_network():
    try:
        socket.create_connection(("www.google.com", 80))
        return False
    except (OSError, IOError):
        pass
    return True


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class AutoProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for auto"""

    provider_name = "auto"
    domain = "pacalis.net"

    def _filter_headers(self):
        return ["X-Ovh-Application", "X-Ovh-Consumer", "X-Ovh-Signature"]

    def _test_parameters_overrides(self):
        return {"auth_entrypoint": "ovh-eu"}

    def _test_fallback_fn(self):
        return lambda x: "placeholder_" + x if x != "mapping_override" else None

    # Here we do not mock the function _get_ns_records_domains_for_domain
    # to effectively test the nslookup call and processing.\
    @pytest.mark.skipif(
        _there_is_no_network(), reason="No network, no nslookup call possible."
    )
    def test_nslookup_resolution(self):
        """Ensure that nameservers can be resolved through os nslookup call."""
        assert _get_ns_records_domains_for_domain("google.com")
