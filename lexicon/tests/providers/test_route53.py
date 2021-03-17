"""Test for route53 implementation of the interface."""
# pylint: disable=missing-docstring
from unittest import TestCase
from contextlib import contextmanager

import pytest

from lexicon.tests.providers.integration_tests import IntegrationTests
from lexicon.tests.providers.integration_tests import PROVIDER_VCR
from lexicon.tests.providers.integration_tests import EngineOverrideConfigSource


class Route53ProviderTests(TestCase, IntegrationTests):
    """Route53 Provider Tests."""

    provider_name = 'route53'
    domain = 'fullcr1stal.tk'

    def _filter_headers(self):
        """Sensitive headers to be filtered."""
        return ['Authorization']

    def test_provider_authenticate_private_zone_only(self):
        with self._use_vcr('IntegrationTests/test_provider_authenticate.yaml'):
            provider = self._build_provider_with_overrides({'private_zone': 'true'})
            with pytest.raises(Exception):
                provider.authenticate()

    def test_provider_authenticate_private_zone_false(self):
        with self._use_vcr('IntegrationTests/test_provider_authenticate.yaml'):
            provider = self._build_provider_with_overrides({'private_zone': 'false'})
            provider.authenticate()
            assert provider.domain_id is not None

    def _build_provider_with_overrides(self, overrides):
        config = self._test_config()
        config.add_config_source(EngineOverrideConfigSource(overrides), 0)
        return self.provider_module.Provider(config)

    @contextmanager
    def _use_vcr(self, path):
        with PROVIDER_VCR.use_cassette(
                self._cassette_path(path),
                filter_headers=self._filter_headers(),
                before_record_response=self._filter_response,
                filter_query_parameters=self._filter_query_parameters(),
                filter_post_data_parameters=self._filter_post_data_parameters()):
            yield
