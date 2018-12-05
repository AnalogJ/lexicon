# Test for one implementation of the interface
from lexicon.providers.hetzner import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

import os
from bs4 import BeautifulSoup

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class HetznerProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'hetzner'
    domain = 'rimek.info'

    def _filter_post_data_parameters(self):
        return ['_username','_password']

    def _filter_headers(self):
        return ['Cookie']

    def _filter_response(self, response):
        for cookie in ['set-cookie', 'Set-Cookie']:
            if cookie in response['headers']:
                del response['headers'][cookie]
        if os.environ.get('LEXICON_LIVE_TESTS', 'false') == 'true':
            filter_body = BeautifulSoup(response['body']['string'], 'html.parser').find(id='center_col')
            if filter_body is None:
                filter_body = BeautifulSoup(response['body']['string'], 'html.parser').find(id='msgbox')
            response['body']['string'] = str(filter_body)
        return response

    def _test_parameters_overrides(self):
        env_username = os.environ.get('LEXICON_HETZNER_AUTH_USERNAME')
        env_password = os.environ.get('LEXICON_HETZNER_AUTH_PASSWORD')
        env_live_tests = os.environ.get('LEXICON_LIVE_TESTS', 'false')
        options = {'auth_username': env_username,
                   'auth_password': env_password,
                   'concatenate': 'no',
                   'propagated': 'no',
                   'live_tests': env_live_tests}
        return options