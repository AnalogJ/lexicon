"""Integration tests for Localzone"""
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests

try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class LocalzoneProviderTests(TestCase, IntegrationTests):
    """Integration tests for Localzone"""
    provider_name = "localzone"
    domain = "example.com"
    file_uri = "https://raw.githubusercontent.com/ags-slc/localzone/master/tests/zonefiles/db.example.com"  # pylint: disable=line-too-long
    filename, headers = urlretrieve(file_uri)

    def _test_parameters_overrides(self):
        options = {
            "filename": self.filename
        }

        return options

    def _test_fallback_fn(self):
        return lambda _: None

    @pytest.mark.skip(reason="localzone does not require authentication")
    def test_provider_authenticate(self):
        return

    @pytest.mark.skip(reason="localzone does not require authentication")
    def test_provider_authenticate_with_unmanaged_domain_should_fail(self):
        return
