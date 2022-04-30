"""Integration tests for Yandex Cloud provider"""
from lexicon.tests.providers.integration_tests import IntegrationTestsV2
from unittest import TestCase


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class YandexCloudProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Yandex cloud provider

    Required following environment variables to run:
    LEXICON_YANDEXCLOUD_AUTH_TOKEN
    LEXICON_YANDEXCLOUD_CLOUD_ID
    LEXICON_YANDEXCLOUD_FOLDER_ID
    """
    provider_name = 'yandexcloud'
    domain = 'example.com'

    def _filter_headers(self):
        return ['Authorization']

    # filter out data which change on each run
    def _filter_response(self, response):
        if 'x-envoy-upstream-service-time' in response['headers']:
            del response['headers']['x-envoy-upstream-service-time']
        if 'x-request-id' in response['headers']:
            del response['headers']['x-request-id']
        if 'x-server-trace-id' in response['headers']:
            del response['headers']['x-server-trace-id']
        if 'grpc-message' in response['headers']:
            del response['headers']['grpc-message']
        if 'grpc-status' in response['headers']:
            del response['headers']['grpc-status']
        return response

    def _test_parameters_overrides(self):
        return {"folder_id": "b1gm2f812hg4h5s5jsgn"}
