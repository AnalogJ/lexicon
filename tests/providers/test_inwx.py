from unittest import TestCase

from lexicon.providers.inwx import Provider
from integration_tests import IntegrationTests


class InwxProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'inwx'
    domain = 'lexicon-testrunner.com'

    def _test_options(self):
        cmd_options = super(InwxProviderTests, self)._test_options()
        # set testing endpoint to inwx ote service
        cmd_options['endpoint'] = 'https://api.ote.domrobot.com/xmlrpc/'
        return cmd_options
