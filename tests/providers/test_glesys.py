# Test for one implementation of the interface
from lexicon.providers.glesys import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class GlesysProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'glesys'
    domain = "capsulecd.com"

    def _filter_headers(self):
        return ['Authorization']
