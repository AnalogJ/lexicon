from unittest import TestCase
from lexicon.providers.onapp import Provider
from integration_tests import IntegrationTests

class OnappProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'onapp'
    domain = 'my-test.org'

    def _filter_headers(self):
        return ['Authorization']