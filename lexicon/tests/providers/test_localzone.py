# Test the localzone implementation of the interface
from unittest import TestCase

import pytest
from lexicon.tests.providers.integration_tests import IntegrationTests
from lexicon.providers.localzone import Provider


try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests


class LocalzoneProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = "localzone"
    domain = "example.com"
    file_uri = "https://raw.githubusercontent.com/ags-slc/localzone/master/tests/zonefiles/db.example.com"
    filename, headers = urlretrieve(file_uri)

    def _test_parameters_overrides(self):
        options = {
            "filename": self.filename
        }

        return options

    def _test_fallback_fn(self):
        return lambda _: None

    @pytest.mark.skip(reason="localzone does not require authentication")
    def test_Provider_authenticate(self):
        return

    @pytest.mark.skip(reason="localzone does not require authentication")
    def test_Provider_authenticate_with_unmanaged_domain_should_fail(self):
        return
