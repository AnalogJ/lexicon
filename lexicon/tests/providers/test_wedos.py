# Test for one implementation of the interface
import json
import re
import urllib.parse

from lexicon.tests.providers.integration_tests import IntegrationTestsV2
from unittest import TestCase


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class WedosProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for wedos provider"""
    provider_name = 'wedos'
    domain = 'kaniok.com'

    def _filter_post_data_parameters(self):
        return ['login_token']

    def _filter_request(self, request):
        request_start_string = 'request='
        try:
            body = urllib.parse.unquote_plus(urllib.parse.unquote(request.body.decode()))
            body = re.sub(r'request=', '', body)
            data = json.loads(body)
        except ValueError:
            pass
        else:
            data['request']['user'] = 'username'
            data['request']['auth'] = 'password'
            body = request_start_string+json.dumps(data)
            body = urllib.parse.quote(urllib.parse.quote_plus(body.encode()))
            request.body = body

        return request

    def _filter_headers(self):
        return ['Authorization']

    def _filter_query_parameters(self):
        return ['secret_key']

    def _filter_response(self, response):
        """See `IntegrationTests._filter_response` for more information on how
        to filter the provider response."""

        return response
