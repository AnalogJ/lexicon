from unittest import TestCase

from lexicon.providers.inwx import Provider
from integration_tests import IntegrationTests


class InwxProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'inwx'
    domain = 'lexicon-testrunner.com'

    def _test_parameters_overrides(self):
        return {
            'endpoint': 'https://api.ote.domrobot.com/xmlrpc/'
        }

