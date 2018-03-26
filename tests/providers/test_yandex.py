# Test for one implementation of the interface
from lexicon.providers.yandex import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class YandexPDDProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'yandex'
    domain = 'capsulecd.com'

    def _filter_headers(self):
        """Sensitive headers to be filtered."""
        return ['Authorization', 'PddToken']
