# Test for one implementation of the interface
from lexicon.providers.dnspark import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsParkProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'dnspark'
    domain = 'capsulecd.com'
    def _filter_headers(self):
        return ['Authorization']
