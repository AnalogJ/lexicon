"""Integration tests for CloudXNS"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests


class CloudXNSProviderTests(TestCase, IntegrationTests):
    """TestCase for CloudXNS"""
    provider_name = 'cloudxns'
    domain = 'capsulecd.com'

    def _filter_post_data_parameters(self):
        return ['login_token']

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(self):
        return

    def _test_parameters_overrides(self):
        return {'api_endpoint': 'https://www.cloudxns.net/api2'}
