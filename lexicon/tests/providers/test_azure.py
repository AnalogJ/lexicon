"""Integration tests for Azure Cloud DNS"""
import re

from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests


class AzureTests(TestCase, IntegrationTests):
    """TestCase for Google Cloud DNS"""
    provider_name = 'azure'
    domain = 'full4ir.tk'

    def _test_parameters_overrides(self):
        return {'resource_group': 'dns-test'}

    def _filter_headers(self):
        return [('Authorization', 'Bearer TOKEN')]

    def _filter_post_data_parameters(self):
        return [('client_id', 'CLIENT_ID'), ('client_secret', 'CLIENT_SECRET')]

    def _filter_request(self, request):
        # Hide auth_tenant_id value in oauth token requests
        request.uri = re.sub(r'/[\w-]+/oauth2/token', '/TENANT_ID/oauth2/token',
                             request.uri)
        # Hide auth_subscription_id value in DNS requests
        request.uri = re.sub(r'/subscriptions/[\w-]+/', '/subscriptions/SUBSCRIPTION_ID/',
                             request.uri)
        return request

    def _filter_response(self, response):
        # Hide access_token value in oauth token responses
        response['body']['string'] = re.sub(
            br'"access_token":"[\w.-]+"', b'"access_token":"TOKEN"',
            response['body']['string'])
        response['body']['string'] = re.sub(
            br'\\/subscriptions\\/[\w-]+\\/', b'\\/subscriptions\\/SUBSCRIPTION_ID\\/',
            response['body']['string'])
        return response
