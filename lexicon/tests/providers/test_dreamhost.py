"""Integration tests for Dreamhost"""
from unittest import TestCase

import pytest

from lexicon.providers.dreamhost import Provider
from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class DreamhostProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Dreamhost"""

    provider_name = "dreamhost"
    domain = "lexicon-example.com"

    def _filter_query_parameters(self):
        return ["key"]

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return

    def test_identifier(self):
        """Test _identifier"""
        dreamhost_record = {
            "type": "A",
            "record": "www.example.com",
            "value": "1.2.3.4",
        }
        identifier = Provider._identifier(dreamhost_record)

        dreamhost_record_from_id = Provider._id_to_dreamhost_record(identifier)

        assert dreamhost_record_from_id == dreamhost_record

    def test_id_to_record(self):
        """Test _id_to_record and _record_to_dreamhost_record"""
        dreamhost_record = {
            "type": "A",
            "record": "www.example.com",
            "value": "1.2.3.4",
        }

        identifier = Provider._identifier(dreamhost_record)

        record = Provider._id_to_record(identifier)
        dreamhost_record_from_id = Provider._record_to_dreamhost_record(record)

        assert dreamhost_record_from_id == dreamhost_record

    def test_id_to_dreamhost_record(self):
        """Test _id_to_dreamhost_record"""
        dreamhost_record = {
            "type": "A",
            "record": "www.example.com",
            "value": "1.2.3.4",
        }

        identifier = Provider._identifier(dreamhost_record)

        dreamhost_record_from_id = Provider._id_to_dreamhost_record(identifier)

        assert dreamhost_record_from_id == dreamhost_record
