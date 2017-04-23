"""Test for route53 implementation of the interface."""
import unittest
import pytest
from lexicon.providers.route53 import Provider
from integration_tests import IntegrationTests


class Route53ProviderTests(unittest.TestCase, IntegrationTests):
    """Route53 Proivder Tests."""

    Provider = Provider
    provider_name = 'route53'
    domain = 'capsulecd.com'

    def _filter_headers(self):
        """Sensitive headers to be filtered."""
        return ['Authorization']

    @pytest.mark.skip(reason="route 53 dns records don't have ids")
    def test_Provider_when_calling_delete_record_by_identifier_should_remove_record(self):
        return

    # TODO: this should be enabled
    @pytest.mark.skip(reason="regenerating auth keys required")
    def test_Provider_when_calling_update_record_should_modify_record_name_specified(self):
        return