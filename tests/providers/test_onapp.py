from unittest import TestCase

from integration_tests import IntegrationTests
from lexicon.providers.onapp import Provider


class OnappProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'onapp'
    domain = 'my-test.org'

    def _filter_headers(self):
        return ['Authorization']

    def _test_parameters_overrides(self):
        return {'auth_server': 'https://dashboard.dynomesh.com.au'}
