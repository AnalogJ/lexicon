"""Integration tests for Hetzner"""
from unittest import TestCase
import os

import mock
import pytest

from lexicon.tests.providers.integration_tests import IntegrationTests


def _no_dns_lookup():
    try:
        import dns.resolver
    except ImportError:
        return False

    _domains = ['rimek.info', 'bettilaila.com']
    _resolver = dns.resolver.Resolver()
    _resolver.lifetime = 1
    try:
        for _domain in _domains:
            _ = dns.resolver.zone_for_name(_domain, resolver=_resolver)
        return False
    except dns.exception.DNSException:
        pass
    return True


class HetznerIntegrationTests(IntegrationTests):
    """Base TestCase for Hetzner"""
    @pytest.fixture(autouse=True)
    def _dns_cname_mock(self, request):
        _ignore_mock = request.node.get_closest_marker('ignore_dns_cname_mock')
        _domain_mock = self.domain
        if request.node.name == 'test_provider_authenticate_with_unmanaged_domain_should_fail':
            _domain_mock = 'thisisadomainidonotown.com'
        if _ignore_mock:
            yield
        else:
            with mock.patch('lexicon.providers.hetzner.Provider._get_dns_cname',
                            return_value=(_domain_mock, [], None)) as fixture:
                yield fixture

    @pytest.mark.skipif(_no_dns_lookup(), reason='No DNS resolution possible.')
    @pytest.mark.ignore_dns_cname_mock
    def _test_get_dns_cname(self):
        """Ensure that zone for name can be resolved through dns.resolver call."""
        _domain, _nameservers, _cname = self.provider_module.Provider._get_dns_cname(  # pylint: disable=protected-access
            ('_acme-challenge.fqdn.{}.'.format(self.domain)), False)

        assert _domain == self.domain
        assert _nameservers
        assert not _cname


class HetznerRobotProviderTests(TestCase, HetznerIntegrationTests):
    """TestCase for Hetzner Robot"""
    provider_name = 'hetzner'
    provider_variant = 'Robot'
    domain = 'rimek.info'

    def _filter_post_data_parameters(self):
        return ['_username', '_password', '_csrf_token']

    def _filter_headers(self):
        return ['Cookie']

    def _filter_response(self, response):
        from bs4 import BeautifulSoup

        for cookie in ['set-cookie', 'Set-Cookie']:
            if cookie in response['headers']:
                del response['headers'][cookie]
        if os.environ.get('LEXICON_LIVE_TESTS', 'false') == 'true':
            filter_body = (BeautifulSoup(response['body']['string'], 'html.parser')
                           .find(id='center_col'))
            if not filter_body:
                filter_body = (BeautifulSoup(response['body']['string'], 'html.parser')
                               .find(id='login-form'))
            response['body']['string'] = str(filter_body).encode('UTF-8')
        return response

    def _test_parameters_overrides(self):
        options = {'auth_account': 'robot',
                   'linked': 'no',
                   'propagated': 'no',
                   'latency': 0.00001}
        return options


class HetznerKonsoleHProviderTests(TestCase, HetznerIntegrationTests):
    """TestCase for KonsoleH"""
    provider_name = 'hetzner'
    provider_variant = 'KonsoleH'
    domain = 'bettilaila.com'

    def _filter_post_data_parameters(self):
        return ['login_user_inputbox', 'login_pass_inputbox', '_csrf_name', '_csrf_token']

    def _filter_headers(self):
        return ['Cookie']

    def _filter_response(self, response):
        from bs4 import BeautifulSoup

        for cookie in ['set-cookie', 'Set-Cookie']:
            if cookie in response['headers']:
                del response['headers'][cookie]
        if os.environ.get('LEXICON_LIVE_TESTS', 'false') == 'true':
            filter_body = (BeautifulSoup(response['body']['string'], 'html.parser')
                           .find(id='content'))
            if not filter_body:
                filter_body = (BeautifulSoup(response['body']['string'], 'html.parser')
                               .find(id='loginform'))
            response['body']['string'] = str(filter_body).encode('UTF-8')
        return response

    def _test_parameters_overrides(self):
        env_username = os.environ.get('LEXICON_HETZNER_KONSOLEH_USERNAME', 'placeholder_username')
        env_password = os.environ.get('LEXICON_HETZNER_KONSOLEH_PASSWORD', 'placeholder_password')
        options = {'auth_account': 'konsoleh',
                   'auth_username': env_username,
                   'auth_password': env_password,
                   'linked': 'no',
                   'propagated': 'no',
                   'latency': 0.00001}
        return options
