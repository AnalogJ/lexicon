# Test for one implementation of the interface
from unittest import TestCase
from lexicon.providers.godaddy import Provider
from integration_tests import IntegrationTests

import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests


class GoDaddyProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'godaddy'
    domain = 'fullm3tal.online'

    def _filter_headers(self):
        return ['Authorization']
