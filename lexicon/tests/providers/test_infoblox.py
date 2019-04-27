"""
A note about running these tests against a Infoblox Environment

1. Make sure the NIOS Version support WAPI 2.6.1
2. Have a valid Certificate from a public CA installed at the Infoblox
3. Create a Authoritative zone test.local in a view (default if no views are created)
4. Create a User with permissions RW permissions
   for the zone test.local and enable the User for API

Environment Variables work fine when envoking lexicon manually
LEXICON_INFOBLOX_AUTH_USER={user} LEXICON_INFOBLOX_AUTH_PSW={password}
    lexicon infoblox --ib-host dns1.int.metro-cc.com --ib-view internal
        create test.local A --content 10.10.10.11 --name lexicon1
Invoking the py.test however fails
LEXICON_LIVE_TESTS=true LEXICON_INFOBLOX_AUTH_USER={username} LEXICON_INFOBLOX_AUTH_PSW={password}
    py.test tests/providers/test_infoblox.py
Both parameters are populated with:
auth_user = placeholder_auth_user
auth_psw = placeholder_auth_psw
"""
import os
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class InfobloxProviderTests(TestCase, IntegrationTests):
    """TestCase for Infoblox"""
    provider_name = 'infoblox'
    domain = 'test.local'

    def _test_parameters_overrides(self):
        # Workaround ENV problems during testing
        env_user = os.environ.get('LEXICON_INFOBLOX_AUTH_USER', 'infoblox')
        env_psw = os.environ.get('LEXICON_INFOBLOX_AUTH_PSW', 'default')
        return {'ib_host': 'dns1.int.metro-cc.com', 'ib_view': 'internal',
                'auth_user': env_user, 'auth_psw': env_psw}

    def _filter_headers(self):
        return ['Authorization', 'Cookie', 'set-cookie']
