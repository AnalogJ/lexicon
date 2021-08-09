"""Base class for provider integration tests"""
import os
from functools import wraps
from importlib import import_module
from typing import Optional

import pytest
import vcr  # type: ignore

from lexicon.config import ConfigResolver, ConfigSource, DictConfigSource

# Configure VCR. Parameter record_mode depends on the LEXICON_LIVE_TESTS environment variable value.
RECORD_MODE = "none"
if os.environ.get("LEXICON_LIVE_TESTS", "false") == "true":
    RECORD_MODE = "once"
PROVIDER_VCR = vcr.VCR(
    cassette_library_dir=os.environ.get(
        "LEXICON_VCRPY_CASSETTES_PATH", "tests/fixtures/cassettes"
    ),
    record_mode=RECORD_MODE,
    decode_compressed_response=True,
)


# Prepare custom decorator: it will start a casette in relevant folder for current provider,
# and using the name of the test method as the cassette's name.
def _vcr_integration_test(decorated):
    @wraps(decorated)
    def wrapper(self):
        with PROVIDER_VCR.use_cassette(
            self._cassette_path(f"IntegrationTests/{decorated.__name__}.yaml"),
            filter_headers=self._filter_headers(),
            filter_query_parameters=self._filter_query_parameters(),
            filter_post_data_parameters=self._filter_post_data_parameters(),
            before_record_request=self._filter_request,
            before_record_response=self._filter_response,
        ):
            decorated(self)
        # pylint: enable=protected-access

    return wrapper


class EngineOverrideConfigSource(ConfigSource):
    """Config source to override some provider parameters during tests"""

    def __init__(self, overrides):
        super(EngineOverrideConfigSource, self).__init__()
        self.overrides = overrides

    def resolve(self, config_key):
        # We extract the key from existing namespace.
        config_key = config_key.split(":")[-1]
        return self.overrides.get(config_key)


class FallbackConfigSource(ConfigSource):
    """Config source to provider fallback to provider parameters during tests"""

    def __init__(self, fallback_fn):
        super(FallbackConfigSource, self).__init__()
        self.fallback_fn = fallback_fn

    def resolve(self, config_key):
        config_key = config_key.split(":")
        if not config_key[-2] == "lexicon":
            return self.fallback_fn(config_key[-1])

        return None


class IntegrationTestsV1(object):
    """
    https://stackoverflow.com/questions/26266481/pytest-reusable-tests-for-different-implementations-of-the-same-interface
    Single, reusable definition of tests for the interface. Authors of
    new implementations of the interface merely have to provide the test
    data, as class attributes of a class which inherits
    unittest.TestCase AND this class.

    Required test data:
    self.Provider must be set
    self.provider_name must be set
    self.domain must be set
    self._filter_headers can be defined to provide a list of sensitive http headers
    self._filter_query_parameters can be defined to provide a list of sensitive query parameters
    self._filter_post_data_parameters can be defined to provide a list of sensitive post data parameters
    self.provider_variant can be defined as a prefix for saving cassettes when a provider uses multiple variants

    IntegrationTestsV1 is used for providers developed before IntegrationTestsV2 has been created.
    """

    def __init__(self):
        self.domain = None
        self.provider_name = None
        self.provider_module = None

    def setup_method(self, _):
        self.provider_module = import_module(f"lexicon.providers.{self.provider_name}")

    ###########################################################################
    # Provider module shape
    ###########################################################################
    def test_provider_module_shape(self):
        module = import_module(f"lexicon.providers.{self.provider_name}")

        assert hasattr(module, "provider_parser")
        assert hasattr(module, "Provider")
        if self.provider_name != "auto":
            assert hasattr(module, "NAMESERVER_DOMAINS")

        assert callable(module.provider_parser)
        assert callable(module.Provider)
        if self.provider_name != "auto":
            assert isinstance(module.NAMESERVER_DOMAINS, list)

    ###########################################################################
    # Provider.authenticate()
    ###########################################################################
    @_vcr_integration_test
    def test_provider_authenticate(self):
        provider = self._construct_authenticated_provider()
        assert provider.domain_id is not None

    @_vcr_integration_test
    def test_provider_authenticate_with_unmanaged_domain_should_fail(self):
        config = self._test_config()
        config.add_config_source(
            DictConfigSource({"domain": "thisisadomainidonotown.com"}), 0
        )
        provider = self.provider_module.Provider(config)
        with pytest.raises(Exception):
            provider.authenticate()

    ###########################################################################
    # Provider.create_record()
    ###########################################################################
    @_vcr_integration_test
    def test_provider_when_calling_create_record_for_A_with_valid_name_and_content(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("A", "localhost", "127.0.0.1")

    @_vcr_integration_test
    def test_provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("CNAME", "docs", "docs.example.com")

    @_vcr_integration_test
    def test_provider_when_calling_create_record_for_TXT_with_valid_name_and_content(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("TXT", "_acme-challenge.test", "challengetoken")

    @_vcr_integration_test
    def test_provider_when_calling_create_record_for_TXT_with_full_name_and_content(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"_acme-challenge.full.{self.domain}", "challengetoken"
        )

    @_vcr_integration_test
    def test_provider_when_calling_create_record_for_TXT_with_fqdn_name_and_content(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"_acme-challenge.fqdn.{self.domain}.", "challengetoken"
        )

    ###########################################################################
    # Provider.list_records()
    ###########################################################################
    @_vcr_integration_test
    def test_provider_when_calling_list_records_with_no_arguments_should_list_all(self):
        provider = self._construct_authenticated_provider()
        assert isinstance(provider.list_records(), list)

    @_vcr_integration_test
    def test_provider_when_calling_list_records_with_name_filter_should_return_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        provider.create_record("TXT", "random.test", "challengetoken")
        records = provider.list_records("TXT", "random.test")
        assert len(records) == 1
        assert records[0]["content"] == "challengetoken"
        assert records[0]["type"] == "TXT"
        assert records[0]["name"] == f"random.test.{self.domain}"

    @_vcr_integration_test
    def test_provider_when_calling_list_records_with_full_name_filter_should_return_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        provider.create_record(
            "TXT", f"random.fulltest.{self.domain}", "challengetoken"
        )
        records = provider.list_records("TXT", f"random.fulltest.{self.domain}")
        assert len(records) == 1
        assert records[0]["content"] == "challengetoken"
        assert records[0]["type"] == "TXT"
        assert records[0]["name"] == f"random.fulltest.{self.domain}"

    @_vcr_integration_test
    def test_provider_when_calling_list_records_with_fqdn_name_filter_should_return_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        provider.create_record(
            "TXT", f"random.fqdntest.{self.domain}.", "challengetoken"
        )
        records = provider.list_records("TXT", f"random.fqdntest.{self.domain}.")
        assert len(records) == 1
        assert records[0]["content"] == "challengetoken"
        assert records[0]["type"] == "TXT"
        assert records[0]["name"] == f"random.fqdntest.{self.domain}"

    @_vcr_integration_test
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"ttl.fqdn.{self.domain}.", "ttlshouldbe3600"
        )
        records = provider.list_records("TXT", f"ttl.fqdn.{self.domain}")
        assert len(records) == 1
        assert str(records[0]["ttl"]) == str(3600)

    @pytest.mark.skip(
        reason="not sure how to test empty list across multiple providers"
    )
    @_vcr_integration_test
    def test_provider_when_calling_list_records_should_return_empty_list_if_no_records_found(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert isinstance(provider.list_records(), list)

    @pytest.mark.skip(reason="not sure how to test filtering across multiple providers")
    @_vcr_integration_test
    def test_provider_when_calling_list_records_with_arguments_should_filter_list(self):
        provider = self._construct_authenticated_provider()
        assert isinstance(provider.list_records(), list)

    ###########################################################################
    # Provider.update_record()
    ###########################################################################
    @_vcr_integration_test
    def test_provider_when_calling_update_record_should_modify_record(self):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("TXT", "orig.test", "challengetoken")
        records = provider.list_records("TXT", "orig.test")
        assert provider.update_record(
            records[0].get("id", None), "TXT", "updated.test", "challengetoken"
        )

    @_vcr_integration_test
    def test_provider_when_calling_update_record_should_modify_record_name_specified(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("TXT", "orig.nameonly.test", "challengetoken")
        assert provider.update_record(None, "TXT", "orig.nameonly.test", "updated")

    @_vcr_integration_test
    def test_provider_when_calling_update_record_with_full_name_should_modify_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"orig.testfull.{self.domain}", "challengetoken"
        )
        records = provider.list_records("TXT", f"orig.testfull.{self.domain}")
        assert provider.update_record(
            records[0].get("id", None),
            "TXT",
            f"updated.testfull.{self.domain}",
            "challengetoken",
        )

    @_vcr_integration_test
    def test_provider_when_calling_update_record_with_fqdn_name_should_modify_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"orig.testfqdn.{self.domain}.", "challengetoken"
        )
        records = provider.list_records("TXT", f"orig.testfqdn.{self.domain}.")
        assert provider.update_record(
            records[0].get("id", None),
            "TXT",
            f"updated.testfqdn.{self.domain}.",
            "challengetoken",
        )

    ###########################################################################
    # Provider.delete_record()
    ###########################################################################
    @_vcr_integration_test
    def test_provider_when_calling_delete_record_by_identifier_should_remove_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("TXT", "delete.testid", "challengetoken")
        records = provider.list_records("TXT", "delete.testid")
        assert provider.delete_record(records[0]["id"])
        records = provider.list_records("TXT", "delete.testid")
        assert not records

    @_vcr_integration_test
    def test_provider_when_calling_delete_record_by_filter_should_remove_record(self):
        provider = self._construct_authenticated_provider()
        assert provider.create_record("TXT", "delete.testfilt", "challengetoken")
        assert provider.delete_record(None, "TXT", "delete.testfilt", "challengetoken")
        records = provider.list_records("TXT", "delete.testfilt")
        assert not records

    @_vcr_integration_test
    def test_provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"delete.testfull.{self.domain}", "challengetoken"
        )
        assert provider.delete_record(
            None, "TXT", f"delete.testfull.{self.domain}", "challengetoken"
        )
        records = provider.list_records("TXT", f"delete.testfull.{self.domain}")
        assert not records

    @_vcr_integration_test
    def test_provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"delete.testfqdn.{self.domain}.", "challengetoken"
        )
        assert provider.delete_record(
            None, "TXT", f"delete.testfqdn.{self.domain}.", "challengetoken"
        )
        records = provider.list_records("TXT", f"delete.testfqdn.{self.domain}.")
        assert not records

    # Private helpers, mimicking the auth_* options provided by the Client
    # http://stackoverflow.com/questions/6229073/how-to-make-a-python-dictionary-that-returns-key-for-keys-missing-from-the-dicti

    def _test_config(self):
        """
        This method construct a ConfigResolver suitable for tests.
        This will resolve any parameters required by Lexicon or the provider in the following order:
            * parameters that matches the ones provided by _test_parameters_overrides
            * parameters that matches existing environment variables at the time of test execution
            * parameters processed throught the lambda provided by _test_fallback_fn.

        See lexicon/providers/base.py for a full list of parameters available.
        You should not override this method. Just override `self.domain`,
        or use _test_parameters_overrides() to configure specific parameters for the tests.

        Any parameters that you expect to be passed to the provider via the cli,
        like --auth_username and --auth_token, will be present during the tests,
        with a 'placeholder_' prefix.

        options['auth_password'] == 'placeholder_auth_password'
        options['auth_username'] == 'placeholder_auth_username'
        options['unique_provider_option'] == 'placeholder_unique_provider_option'

        You can change this behavior by overriding _test_fallback_fn().

        """
        config = ConfigResolver()
        # First we load the overrides
        overrides = self._test_parameters_overrides()
        overrides["domain"] = self.domain
        overrides["provider_name"] = self.provider_name
        config.with_config_source(EngineOverrideConfigSource(overrides))

        # Then we get environment variables
        config.with_env()

        # And finally we provide the fallback function
        config.with_config_source(FallbackConfigSource(self._test_fallback_fn()))

        return config

    def _test_parameters_overrides(self):
        """
        This method gives an object whose keys are some provider
        or lexicon parameters expected during a test.
        If a parameter match on of the key during a test,
        the associated value will be used authoritatively.

        Example:
        {'auth_token': 'AUTH_TOKEN'} => if the provider require to use auth_token,
                                        its value will be always AUTH_TOKEN.

        By default no value is overriden.
        """
        return {}

    def _test_fallback_fn(self):
        """
        This method gives a fallback lambda for any provider parameter that have not been resolved.
        By default it will return 'placeholder_[parameter_name]' for a particular parameter
        (eg. placeholder_auth_token for auth_token).
        """
        return lambda x: "placeholder_" + x

    def _cassette_path(self, fixture_subpath):
        """
        A path customized for the provider's fixture.
        The default path is, for example:
            {provider}/IntegrationTests
        but if the test is a `provider_variant`, the path is customized to the variant:
            {provider}/{variant_name}-IntegrationTests
        """
        if self.provider_variant:
            return f"{self.provider_name}/{self.provider_variant}-{fixture_subpath}"
        return f"{self.provider_name}/{fixture_subpath}"

    def _construct_authenticated_provider(self):
        """
        Construct a new provider, and authenticate it against the target DNS provider API.
        """
        provider = self.provider_module.Provider(self._test_config())
        provider.authenticate()
        return provider

    # Optional. Used to identify the test variant, if any.
    provider_variant: Optional[str] = None

    def _filter_headers(self):
        return []

    def _filter_query_parameters(self):
        return []

    def _filter_post_data_parameters(self):
        return []

    def _filter_request(self, request):
        """Filter any sensitive data out of the provider requests. `request`
        is a Python object with the same structure as all the request sections
        in the YAML recordings at tests/fixtures/cassettes/[provider]. For the
        sake of sparing you some time the most important values are:

        request['body']['string']: Contains the HTML or JSON request body.
        request['uri']: The URI used for this request (URL + parameters)
        response['headers']: An object whose keys are HTTP header names
                             e.g. request['headers']['Accept'].
        """
        return request

    def _filter_response(self, response):
        """Filter any sensitive data out of the provider responses. `response`
        is a Python object with the same structure as all the response sections
        in the YAML recordings at tests/fixtures/cassettes/[provider]. For the
        sake of sparing you some time the most important values are:

        response['body']['string']: Contains the HTML or JSON response body.
        response['headers']: An object whose keys are HTTP header names
                             e.g. response['headers']['content-length'].
        response['status']: An object that contains 'code' and 'message'
                            subkeys representing the HTTP status code and
                            status message.
        """
        return response


class IntegrationTestsV2(IntegrationTestsV1):
    """
    New version of the reusable IntegrationTests class, that includes all tests from
    IntegrationTestsV1, plus new tests related to validation for Create Record NOOP & Record Sets.

    IntegrationTestsV2 should be used for new providers, and for existing providers during
    their refactoring.
    """

    @_vcr_integration_test
    def test_provider_when_calling_create_record_with_duplicate_records_should_be_noop(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"_acme-challenge.noop.{self.domain}.", "challengetoken"
        )
        assert provider.create_record(
            "TXT", f"_acme-challenge.noop.{self.domain}.", "challengetoken"
        )
        records = provider.list_records("TXT", f"_acme-challenge.noop.{self.domain}.")
        assert len(records) == 1

    @_vcr_integration_test
    def test_provider_when_calling_create_record_multiple_times_should_create_record_set(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"_acme-challenge.createrecordset.{self.domain}.", "challengetoken1"
        )
        assert provider.create_record(
            "TXT", f"_acme-challenge.createrecordset.{self.domain}.", "challengetoken2"
        )

    @_vcr_integration_test
    def test_provider_when_calling_list_records_with_invalid_filter_should_be_empty_list(
        self,
    ):
        provider = self._construct_authenticated_provider()
        records = provider.list_records("TXT", f"filter.thisdoesnotexist.{self.domain}")
        assert not records

    @_vcr_integration_test
    def test_provider_when_calling_list_records_should_handle_record_sets(self):
        provider = self._construct_authenticated_provider()
        provider.create_record(
            "TXT", f"_acme-challenge.listrecordset.{self.domain}.", "challengetoken1"
        )
        provider.create_record(
            "TXT", f"_acme-challenge.listrecordset.{self.domain}.", "challengetoken2"
        )
        records = provider.list_records(
            "TXT", f"_acme-challenge.listrecordset.{self.domain}."
        )
        assert len(records) == 2

    @_vcr_integration_test
    def test_provider_when_calling_delete_record_with_record_set_name_remove_all(self):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT", f"_acme-challenge.deleterecordset.{self.domain}.", "challengetoken1"
        )
        assert provider.create_record(
            "TXT", f"_acme-challenge.deleterecordset.{self.domain}.", "challengetoken2"
        )

        assert provider.delete_record(
            None, "TXT", f"_acme-challenge.deleterecordset.{self.domain}."
        )
        records = provider.list_records(
            "TXT", f"_acme-challenge.deleterecordset.{self.domain}."
        )
        assert not records

    @_vcr_integration_test
    def test_provider_when_calling_delete_record_with_record_set_by_content_should_leave_others_untouched(
        self,
    ):
        provider = self._construct_authenticated_provider()
        assert provider.create_record(
            "TXT",
            f"_acme-challenge.deleterecordinset.{self.domain}.",
            "challengetoken1",
        )
        assert provider.create_record(
            "TXT",
            f"_acme-challenge.deleterecordinset.{self.domain}.",
            "challengetoken2",
        )

        assert provider.delete_record(
            None,
            "TXT",
            f"_acme-challenge.deleterecordinset.{self.domain}.",
            "challengetoken1",
        )
        records = provider.list_records(
            "TXT", f"_acme-challenge.deleterecordinset.{self.domain}."
        )
        assert len(records) == 1
