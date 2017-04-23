# Test for one implementation of the interface
from lexicon.providers.cloudxns import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from define_tests.TheTests
class DnsParkProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'cloudxns'
    domain = 'capsulecd.com'
    def _filter_post_data_parameters(self):
        return ['login_token']

    # TODO: this should be enabled
    @pytest.mark.skip(reason="regenerating auth keys required")
    def test_Provider_when_calling_update_record_should_modify_record_name_specified(self):
        return