"""Integration tests for Rage4"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class Rage4ProviderTests(TestCase, IntegrationTests):
    """TestCase for Rage4"""
    provider_name = 'rage4'
    domain = 'capsulecd.com'

    def _filter_headers(self):
        return ['Authorization']

    @pytest.mark.skip(reason="update requires type to be specified for this provider")
    def test_provider_when_calling_update_record_with_full_name_should_modify_record(self):
        return

    @pytest.mark.skip(reason="update requires type to be specified for this provider")
    def test_provider_when_calling_update_record_should_modify_record(self):
        return

    # TODO: the following skipped suite and fixtures should be enabled
    @pytest.mark.skip(reason="new test, missing recording")
    def test_provider_when_calling_update_record_should_modify_record_name_specified(self):
        return
