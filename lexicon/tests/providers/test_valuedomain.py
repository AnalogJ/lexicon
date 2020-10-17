# Test for one implementation of the interface
import pytest

from lexicon.tests.providers.integration_tests import IntegrationTestsV2
from unittest import TestCase


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class ValuedomainProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Value Domain provider"""
    provider_name = 'valuedomain'
    domain = '7io.org'

    def _filter_headers(self):
        return ['Authorization']

    @pytest.mark.skip(reason="record id is not exists")
    def test_provider_when_calling_delete_record_by_identifier_should_remove_record(
        self,
    ):
        return
