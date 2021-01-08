# Test for one implementation of the interface
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class CorenetworksProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Core Networks provider
    shell environment requires
    * LEXICON_CORENETWORKS_AUTH_USERNAME
    * LEXICON_CORENETWORKS_AUTH_PASSWORD
    * LEXICON_CORENETWORKS_API_ENDPOINT"""
    provider_name = 'corenetworks'
    domain = '***REMOVED***'
    endpoint = 'https://beta.api.core-networks.de'

    def _filter_post_data_parameters(self):
        return ['login', 'password']

    def _filter_headers(self):
        return ['Authorization']

    def _filter_query_parameters(self):
        return ['secret_key']

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
        to filter the provider response."""
        return response

    def _test_parameters_overrides(self):
        return {
            'api_endpoint': 'https://beta.api.core-networks.de',
            }
