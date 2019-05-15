"""Integration tests for GratisDNS"""
from unittest import TestCase

import re
# import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests
from lexicon.providers.gratisdns import Provider


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class GratisDNSProviderTests(TestCase, IntegrationTests):
    """TestCase for GratisDNS"""
    Provider = Provider
    provider_name = 'gratisdns'
    domain = 'denisa.dk'
    gratisdns_session = '0123456789abcdef0123456789abcdef'

    def _filter_post_data_parameters(self):
        return ['login', 'password']

    def _filter_headers(self):
        return ['Cookie']

    def _replace_auth(self, cookie):
        cookie = re.sub('ORGID=.*;',
                        'ORGID={};'.format(self.gratisdns_session),
                        cookie)
        return cookie

    # Inspired by thehover provider
    def _filter_response(self, response):
        if 'basestring' not in globals():
            basestring = str

        if 'set-cookie' in response['headers']:
            if isinstance(response['headers']['set-cookie'], basestring):
                response['headers']['set-cookie'] = \
                    self._replace_auth(response['headers']['set-cookie'])
            else:
                for i, cookie in enumerate(response['headers']['set-cookie']):
                    response['headers']['set-cookie'][i] = self._replace_auth(cookie)

        return response
