"""Integration tests for DirectAdmin"""
from lexicon.tests.providers.integration_tests import IntegrationTests
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse the
# tests which *each and every* implementation of the interface must pass, by
# inheritance from integration_tests.IntegrationTests
class DirectAdminProviderTests(TestCase, IntegrationTests):
    """Integration tests for DirectAdmin provider"""
    provider_name = 'directadmin'
    domain = 'example.com'
    endpoint = 'http://localhost'

    def _filter_post_data_parameters(self):
        return []

    def _filter_headers(self):
        return ['Authorization']

    def _filter_query_parameters(self):
        return []

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
           to filter the provider response."""

        # The server against which the live tests run has more domains than
        # relevant for the integration tests, these should not be captured in
        # recordings
        if response['body']['string'][0] != '{':
            # The only non-JSON capable response is the domain list overview,
            # which should be cleaned of unrelated domain information
            response['body']['string'] = 'list[]={0}&list[]=anotherdomain.com'.format(self.domain)
            response['headers']['content-length'] = ['{0}'.format(len(response['body']['string']))]

        return response

    def _test_parameters_overrides(self):
        return {'endpoint': self.endpoint}
