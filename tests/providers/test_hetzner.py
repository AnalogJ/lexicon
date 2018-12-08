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
class HetznerRobotProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'hetzner'
    provider_variant = 'Robot'
    domain = 'rimek.info'

    def _filter_post_data_parameters(self):
        return ['_username','_password', '_csrf_token']

    def _filter_headers(self):
        return ['Cookie']

    def _filter_response(self, response):
        for cookie in ['set-cookie', 'Set-Cookie']:
            if cookie in response['headers']:
                del response['headers'][cookie]
        if os.environ.get('LEXICON_LIVE_TESTS', 'false') == 'true':
            filter_body = BeautifulSoup(response['body']['string'], 'html.parser').find(id='center_col')
            if not filter_body:
                filter_body = BeautifulSoup(response['body']['string'], 'html.parser').find(id='login-form')
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

class HetznerKonsoleHProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'hetzner'
    provider_variant = 'KonsoleH'
    domain = 'bettilaila.com'

    def _filter_post_data_parameters(self):
        return ['login_user_inputbox','login_pass_inputbox', '_csrf_name', '_csrf_token']

    def _filter_headers(self):
        return ['Cookie']

    def _filter_response(self, response):
        for cookie in ['set-cookie', 'Set-Cookie']:
            if cookie in response['headers']:
                del response['headers'][cookie]
        if os.environ.get('LEXICON_LIVE_TESTS', 'false') == 'true':
            filter_body = BeautifulSoup(response['body']['string'], 'html.parser').find(id='content')
            if not filter_body:
                filter_body = BeautifulSoup(response['body']['string'], 'html.parser').find(id='loginform')
            response['body']['string'] = str(filter_body)
        return response

    def _test_parameters_overrides(self):
        env_username = os.environ.get('LEXICON_HETZNER_KONSOLEH_USERNAME')
        env_password = os.environ.get('LEXICON_HETZNER_KONSOLEH_PASSWORD')
        env_live_tests = os.environ.get('LEXICON_LIVE_TESTS', 'false')
        options = {'auth_account': 'konsoleh',
                   'auth_username': env_username,
                   'auth_password': env_password,
                   'concatenate': 'no',
                   'propagated': 'no',
                   'live_tests': env_live_tests}
        return options
