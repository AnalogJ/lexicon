"""
A note about running these tests against the live environment

1.  Namecheap offers a Testing Sandbox for their API.
    You must create an account on `sandbox.namecheap.com`, then "apply" for API
    access. It is supposed to be issued automatically, but you will most-likely
    need to ask their support to approve API access on the test system. You can
    do this via their LiveChat

    https://www.namecheap.com/support/api/methods.aspx

2.  There are two variants of the test:
    * NamecheapProviderTests
    * NamecheapManagedProviderTests

    Namecheap acts a little differently for "owned" vs "managed" domains, so a
    secondary test run must be done.

To set enable live testing against the actual API:

* Create two (2) Sandbox accounts on Namecheap
* Using the First Account:
    *   Enable API access
    *   "Purchase" a first test domain for use on `NamecheapProviderTests`.
        This will be the env variable `LEXICON_NAMECHEAP_DOMAIN`
* Using the Second Account:
    *   "Purchase" a second test domain for use on `NamecheapManagedProviderTests`.
        This will be the env variable `LEXICON_NAMECHEAP_DOMAINMANAGED`
    *   Using the Namecheap dashboard, "share" the domain management with the
        first user.
*   The First account will then get an email to "accept" the domain management
    invitation from the Second account.
*   All API tests occure on the First account
*   Note: Namecheap's API requires the client's IP address to be whitelisted.

The required Environment Variables for a live test are:

    export LEXICON_NAMECHEAP_TOKEN={TOKEN}
    export LEXICON_NAMECHEAP_USERNAME={USERNAME}
    export LEXICON_NAMECHEAP_DOMAIN={DOMAIN_1}
    export LEXICON_NAMECHEAP_DOMAINMANAGED={DOMAIN_2}
"""
import os
from unittest import TestCase

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class NamecheapProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Namecheap"""

    provider_name = "namecheap"

    @property
    def domain(self):
        """
        this can be used to override the tests
            LEXICON_NAMECHEAP_DOMAIN
        """
        env_domain = os.environ.get("LEXICON_NAMECHEAP_DOMAIN", None)
        return env_domain or "unittest2.dev"

    def _filter_query_parameters(self):
        return ["ApiKey", "UserName", "ApiUser"]

    def _test_parameters_overrides(self):
        return {"auth_sandbox": True, "auth_client_ip": "127.0.0.1"}

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return


class NamecheapManagedProviderTests(NamecheapProviderTests):
    """
    The Namecheap API behaves differently for domains that are "Managed" by an
    account instead of "Owned" by the account.  Some endpoints won't work;
    others return different data.

    In orde to handle this, we run the tests on a second domain owned by another
    namecheap customer, but permissioned to this account.

    Note we define a `provider_variant`, which will change the cassette path.
    """

    provider_variant = "managed"

    @property
    def domain(self):
        """
        this can be used to override the tests
            LEXICON_NAMECHEAP_DOMAINMANAGED
        """
        env_domain = os.environ.get("LEXICON_NAMECHEAP_DOMAINMANAGED", None)
        return env_domain or "unittest-seconddomain.dev"
