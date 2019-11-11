"""Integration tests for Dynu.com"""
from unittest import TestCase
import json

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class DynuProviderTests(TestCase, IntegrationTests):
    """TestCase for Dynu.com"""
    provider_name = 'dynu'
    domain = 'example.com'

    def _filter_headers(self):
        return ['API-Key']

    def _filter_response(self, response):
        resp = json.loads(response['body']['string'])
        for resp_domain in resp['domains']:
            resp_domain['name'] = 'example.com'
            resp_domain['unicodeName'] = 'example.com'
            resp_domain['location'] = 'lexicon-dns'
            resp_domain['group'] = 'lexicon-dns'
            resp_domain['ipv4Address'] = '127.0.0.1'
            resp_domain['ipv6Address'] = '::1'

        response['body']['string'] = json.dumps(resp)
        return response
