"""Integration tests for Cloudflare"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CloudflareProviderTests(TestCase, IntegrationTests):
    """TestCase for Cloudflare"""
    provider_name = 'cloudflare'
    domain = 'pacalis.net'

    def _filter_headers(self):
        return ['X-Auth-Email', 'X-Auth-Key', 'set-cookie']

    # We do not want to have "placeholder_auth_username" as default value for `--auth-username`
    # if Bearer tokens are used to execute the tests, because the non-emptiness of this flags
    # triggers interpretation of `--auth-key` as a Global API key.
    # Similarly for `--zone-id`, we want to control when its value is not empty, because
    # it will change the logic of the authentication process.
    def _test_fallback_fn(self):
        return lambda x: 'placeholder_' + x if x not in ('auth_username', 'zone_id') else ''
