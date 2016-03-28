# Test for one implementation of the interface
from lexicon.providers.rage4 import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class Ns1ProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'rage4'
    domain = 'capsulecd.com'
    def _filter_headers(self):
        return ['Authorization']

    @pytest.mark.skip(reason="update requires type to be specified for this provider")
    def test_Provider_when_calling_update_record_with_full_name_should_modify_record(self):
        return