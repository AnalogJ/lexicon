"""Test for route53 implementation of the interface."""
from contextlib import contextmanager
from unittest import TestCase

import pytest

from lexicon.tests.providers import integration_tests


class Route53ProviderTests(TestCase, integration_tests.IntegrationTestsV2):
    """Route53 Provider Tests."""

    provider_name = "route53"
    domain = "fullcr1stal.tk"

    def _filter_headers(self):
        """Sensitive headers to be filtered."""
        return ["Authorization"]

    def test_provider_authenticate_private_zone_only(self):
        with self._use_vcr("IntegrationTests/test_provider_authenticate.yaml"):
            provider = self._build_provider_with_overrides({"private_zone": "true"})
            with pytest.raises(Exception):
                provider.authenticate()

    def test_provider_authenticate_private_zone_false(self):
        with self._use_vcr("IntegrationTests/test_provider_authenticate.yaml"):
            provider = self._build_provider_with_overrides({"private_zone": "false"})
            provider.authenticate()
            assert provider.domain_id is not None

    def _build_provider_with_overrides(self, overrides):
        config = self._test_config()
        config.add_config_source(
            integration_tests.EngineOverrideConfigSource(overrides), 0
        )
        return self.provider_module.Provider(config)

    @contextmanager
    def _use_vcr(self, path):
        with integration_tests.PROVIDER_VCR.use_cassette(
            self._cassette_path(path),
            filter_headers=self._filter_headers(),
            before_record_response=self._filter_response,
            filter_query_parameters=self._filter_query_parameters(),
            filter_post_data_parameters=self._filter_post_data_parameters(),
        ):
            yield
