"""Integration tests for Name.com"""
import json
from unittest import TestCase
from unittest.mock import ANY, Mock, call, patch

import pytest
from integration_tests import IntegrationTestsV2, vcr_integration_test
from requests import HTTPError

from lexicon.config import DictConfigSource
from lexicon._private.providers.namecom import Provider


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class NamecomProviderTests(TestCase, IntegrationTestsV2):
    """TestCase for Name.com"""

    # I don't think we really need some docstrings here.
    # pylint: disable=missing-function-docstring

    provider_name = "namecom"
    domain = "mim.pw"

    def _filter_headers(self):
        return ["Authorization", "Cookie"]

    def _filter_response(self, response):
        headers = response["headers"]
        headers.pop("Set-Cookie", None)
        headers.pop("content-length", None)

        if response["status"]["code"] == 200:
            try:
                data = json.loads(response["body"]["string"].decode())
            except ValueError:
                pass
            else:
                if "records" in data:
                    min_id = 10**8
                    data["records"] = [
                        record for record in data["records"] if record["id"] > min_id
                    ]
                    response["body"]["string"] = json.dumps(data).encode()

        return response

    ###########################
    # Provider.authenticate() #
    ###########################
    @vcr_integration_test
    def test_provider_authentication_method(self):
        provider = self._construct_authenticated_provider()
        assert provider.session.auth

    ############################
    # Provider.create_record() #
    ############################
    @vcr_integration_test
    def test_provider_when_calling_create_record_for_MX_with_priority(
        self,
    ):  # pylint: disable=invalid-name
        priority = 42
        config = self._test_config()
        config.add_config_source(DictConfigSource({"priority": priority}), 0)
        provider = self.provider_module.Provider(config)
        provider.authenticate()

        record_id = provider.create_record("MX", "mx.test1", self.domain)
        assert (
            provider._get_raw_record(record_id)["priority"] == priority
        )  # pylint: disable=protected-access

    @vcr_integration_test
    def test_provider_when_calling_create_record_for_MX_with_no_priority(
        self,
    ):  # pylint: disable=invalid-name
        provider = self._construct_authenticated_provider()
        record_id = provider.create_record("MX", "mx.test2", self.domain)
        assert "priority" not in provider._get_raw_record(
            record_id
        )  # pylint: disable=protected-access

    @vcr_integration_test
    def test_provider_when_calling_create_record_should_fail_on_http_error(self):
        provider = self._construct_authenticated_provider()
        error = HTTPError(response=Mock())
        with patch.object(provider, "_request", side_effect=error):
            with pytest.raises(HTTPError):
                provider.create_record("TXT", "httperror", "HTTPError")

    ############################
    # Provider.update_record() #
    ############################
    @vcr_integration_test
    def test_provider_when_calling_update_record_with_no_identifier_or_rtype_and_name_should_fail(
        self,
    ):  # pylint: disable=line-too-long
        provider = self._construct_authenticated_provider()
        with pytest.raises(ValueError):
            provider.update_record(None)

    @vcr_integration_test
    def test_provider_when_calling_update_record_should_fail_if_no_record_to_update(
        self,
    ):
        provider = self._construct_authenticated_provider()
        with pytest.raises(Exception):
            provider.update_record(None, "TXT", "missingrecord")

    @vcr_integration_test
    def test_provider_when_calling_update_record_should_fail_if_multiple_records_to_update(
        self,
    ):
        provider = self._construct_authenticated_provider()
        provider.create_record("TXT", "multiple.test", "foo")
        provider.create_record("TXT", "multiple.test", "bar")
        with pytest.raises(Exception):
            provider.update_record(None, "TXT", "multiple.test", "updated")

    @vcr_integration_test
    def test_provider_when_calling_update_record_filter_by_content_should_pass(self):
        provider = self._construct_authenticated_provider()
        provider.create_record("TXT", "multiple.test", "foo")
        provider.create_record("TXT", "multiple.test", "bar")
        assert provider.update_record(None, "TXT", "multiple.test", "foo")

    @vcr_integration_test
    def test_provider_when_calling_update_record_by_identifier_with_no_other_args_should_pass(
        self,
    ):
        provider = self._construct_authenticated_provider()
        record_id = provider.create_record("TXT", "update.test", "foo")
        assert provider.update_record(record_id)

    ############################
    # Provider.delete_record() #
    ############################
    @vcr_integration_test
    def test_provider_when_calling_delete_record_with_no_identifier_or_rtype_and_name_should_fail(
        self,
    ):  # pylint: disable=line-too-long
        provider = self._construct_authenticated_provider()
        with pytest.raises(ValueError):
            provider.delete_record()

    @vcr_integration_test
    @patch("lexicon._private.providers.namecom.LOGGER.warning")
    def test_provider_when_calling_delete_record_should_pass_if_no_record_to_delete(
        self, warning
    ):
        provider = self._construct_authenticated_provider()
        provider.delete_record(None, "TXT", "missingrecord")
        warning.assert_called_once()
        assert call("delete_record: there is no record to delete") == warning.call_args


def test_subparser_configuration():
    """Tests the provider_parser method."""

    subparser = Mock()
    Provider.configure_parser(subparser)
    subparser.add_argument.assert_any_call("--auth-username", help=ANY)
    subparser.add_argument.assert_any_call("--auth-token", help=ANY)
