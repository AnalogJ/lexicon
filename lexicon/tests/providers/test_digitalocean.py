"""Integration tests for DigitalOcean"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DigitalOceanProviderTests(TestCase, IntegrationTests):
    """TestCase for DigitalOcean"""
    provider_name = 'digitalocean'
    domain = 'capsulecd.com'

    def _filter_headers(self):
        return ['Authorization']

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return

    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(self):
        return
