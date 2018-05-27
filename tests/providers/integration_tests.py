import contextlib

from builtins import object
import lexicon.client
import lexicon.common.exceptions as lexceptions
import lexicon.common.records as DnsRecords
from lexicon.common.options_handler import SafeOptions, env_auth_options

import pytest
import vcr
import os

# Configure VCR
provider_vcr = vcr.VCR(
        cassette_library_dir='tests/fixtures/cassettes',
        record_mode='new_episodes',
        decode_compressed_response=True
)


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
self._filter_headers can be defined to provide a list of sensitive headers
self._filter_query_parameters can be defined to provide a list of sensitive parameter
self.provider_variant can be defined as a prefix for saving cassettes when a provider uses multiple variants


Extended test suites can be skipped by adding the following snippet to the test_{PROVIDER_NAME}.py file

    @pytest.fixture(autouse=True)
    def skip_suite(self, request):
        if request.node.get_marker('ext_suite_1'):
            pytest.skip('Skipping extended suite')

"""
class IntegrationTests(object):
    ###########################################################################
    # Provider.authenticate()
    ###########################################################################
    def test_Provider_authenticate(self):
        with self._test_fixture_recording('test_Provider_authenticate'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.domain_id is not None

    def test_Provider_authenticate_with_unmanaged_domain_should_fail(self):
        with self._test_fixture_recording('test_Provider_authenticate_with_unmanaged_domain_should_fail'):
            options = self._test_options()
            options['domain'] = 'thisisadomainidonotown.com'
            provider = self.Provider(options, self._test_engine_overrides())
            with pytest.raises(lexceptions.DomainNotFoundError):
                provider.authenticate()

    ###########################################################################
    # Provider.create_record()
    ###########################################################################
    def test_Provider_when_calling_create_record_for_A_with_valid_name_and_content(self):
        with self._test_fixture_recording('test_Provider_when_calling_create_record_for_A_with_valid_name_and_content'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.A_Record(None,'localhost','127.0.0.1'))

    def test_Provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(self):
        with self._test_fixture_recording('test_Provider_when_calling_create_record_for_CNAME_with_valid_name_and_content'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.CNAME_Record(None,'docs','docs.example.com'))

    def test_Provider_when_calling_create_record_for_TXT_with_valid_name_and_content(self):
        with self._test_fixture_recording('test_Provider_when_calling_create_record_for_TXT_with_valid_name_and_content'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,'_acme-challenge.test','challengetoken'))

    def test_Provider_when_calling_create_record_for_TXT_with_full_name_and_content(self):
        with self._test_fixture_recording('test_Provider_when_calling_create_record_for_TXT_with_full_name_and_content'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.full.{0}".format(self.domain),'challengetoken'))

    def test_Provider_when_calling_create_record_for_TXT_with_fqdn_name_and_content(self):
        with self._test_fixture_recording('test_Provider_when_calling_create_record_for_TXT_with_fqdn_name_and_content'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.fqdn.{0}.".format(self.domain),'challengetoken'))

    ###########################################################################
    # Provider.list_records()
    ###########################################################################
    def test_Provider_when_calling_list_records_with_no_arguments_should_list_all(self):
        with self._test_fixture_recording('test_Provider_when_calling_list_records_with_no_arguments_should_list_all'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert isinstance(provider.list_records(), list)

    def test_Provider_when_calling_list_records_with_name_filter_should_return_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_list_records_with_name_filter_should_return_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            provider.create_record(DnsRecords.TXT_Record(None,'random.test','challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'random.test'))
            assert len(records) == 1
            assert records[0].content == 'challengetoken'
            assert records[0].type == 'TXT'
            assert records[0].name == 'random.test.{0}'.format(self.domain)

    def test_Provider_when_calling_list_records_with_full_name_filter_should_return_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_list_records_with_full_name_filter_should_return_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            provider.create_record(DnsRecords.TXT_Record(None,'random.fulltest.{0}'.format(self.domain),'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'random.fulltest.{0}'.format(self.domain)))
            assert len(records) == 1
            assert records[0].content == 'challengetoken'
            assert records[0].type == 'TXT'
            assert records[0].name == 'random.fulltest.{0}'.format(self.domain)

    def test_Provider_when_calling_list_records_with_fqdn_name_filter_should_return_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_list_records_with_fqdn_name_filter_should_return_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            provider.create_record(DnsRecords.TXT_Record(None,'random.fqdntest.{0}.'.format(self.domain),'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'random.fqdntest.{0}.'.format(self.domain)))
            assert len(records) == 1
            assert records[0].content == 'challengetoken'
            assert records[0].type == 'TXT'
            assert records[0].name == 'random.fqdntest.{0}'.format(self.domain)

    def test_Provider_when_calling_list_records_should_return_empty_list_if_no_records_found(self):
        with self._test_fixture_recording('test_Provider_when_calling_list_records_should_return_empty_list_if_no_records_found'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            records = provider.list_records(DnsRecords.TXT_Record(None,'non-existant', 'dummy-value'))
            assert isinstance(records, list)
            assert len(records) == 0

    ###########################################################################
    # Provider.update_record()
    ###########################################################################
    def test_Provider_when_calling_update_record_should_modify_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_update_record_should_modify_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            name = 'update.test'
            assert provider.create_record(DnsRecords.TXT_Record(None,name,'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,name))
            if records[0].id:
                assert provider.update_record(DnsRecords.TXT_Record(records[0].id), DnsRecords.TXT_Record(None,name,'challengetoken','newtoken'))

    def test_Provider_when_calling_update_record_with_full_name_should_modify_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_update_record_with_full_name_should_modify_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            name = 'update.testfull.{0}'.format(self.domain)
            assert provider.create_record(DnsRecords.TXT_Record(None,name,'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,name))
            assert provider.update_record(DnsRecords.TXT_Record(name=name), DnsRecords.TXT_Record(None,name,'challengetoken','newtoken'))

    def test_Provider_when_calling_update_record_with_fqdn_name_should_modify_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_update_record_with_fqdn_name_should_modify_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            name = 'update.testfqdn.{0}'.format(self.domain)
            assert provider.create_record(DnsRecords.TXT_Record(None,name,'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,name))
            assert provider.update_record(DnsRecords.TXT_Record(name=name), DnsRecords.TXT_Record(None,name,'challengetoken','newtoken'))

    def test_Provider_when_calling_update_record_with_non_existant_name_should_throw_error(self):
        with self._test_fixture_recording('test_Provider_when_calling_update_record_with_non_existant_name_should_throw_error'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            name = 'update.notexist'
            records = provider.list_records(DnsRecords.TXT_Record(None,name))
            assert len(records) == 0
            with pytest.raises(lexceptions.RecordNotFoundError):
                provider.update_record(DnsRecords.TXT_Record(None,name,'challengetoken'), DnsRecords.TXT_Record(None,name,'newtoken'))

    ###########################################################################
    # Provider.delete_record()
    ###########################################################################
    def test_Provider_when_calling_delete_record_by_identifier_should_remove_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_delete_record_by_identifier_should_remove_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,'delete.testid','challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'delete.testid'))
            assert provider.delete_record(DnsRecords.TXT_Record(records[0].id))
            records = provider.list_records(DnsRecords.TXT_Record(None,'delete.testid'))
            assert len(records) == 0

    def test_Provider_when_calling_delete_record_by_filter_should_remove_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_delete_record_by_filter_should_remove_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,'delete.testfilt','challengetoken'))
            assert provider.delete_record(DnsRecords.TXT_Record(None,'delete.testfilt','challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'delete.testfilt'))
            assert len(records) == 0

    def test_Provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,'delete.testfull.{0}'.format(self.domain),'challengetoken'))
            assert provider.delete_record(DnsRecords.TXT_Record(None,'delete.testfull.{0}'.format(self.domain),'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'delete.testfull.{0}'.format(self.domain)))
            assert len(records) == 0

    def test_Provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record(self):
        with self._test_fixture_recording('test_Provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,'delete.testfqdn.{0}.'.format(self.domain),'challengetoken'))
            assert provider.delete_record(DnsRecords.TXT_Record(None,'delete.testfqdn.{0}.'.format(self.domain),'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'delete.testfqdn.{0}.'.format(self.domain)))
            assert len(records) == 0

    ###########################################################################
    # Extended Test Suite 1 - March 2018 - Validation for Create Record NOOP & Record Sets
    ###########################################################################

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_create_record_with_duplicate_records_should_be_noop(self):
        with self._test_fixture_recording('test_Provider_when_calling_create_record_with_duplicate_records_should_be_noop'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.noop.{0}.".format(self.domain),'challengetoken'))
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.noop.{0}.".format(self.domain),'challengetoken'))
            records = provider.list_records(DnsRecords.TXT_Record(None,"_acme-challenge.noop.{0}.".format(self.domain)))
            assert len(records) == 1

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_create_record_multiple_times_should_create_record_set(self):
        with self._test_fixture_recording('test_Provider_when_calling_create_record_multiple_times_should_create_record_set'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.createrecordset.{0}.".format(self.domain),'challengetoken1'))
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.createrecordset.{0}.".format(self.domain),'challengetoken2'))

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_list_records_with_invalid_filter_should_be_empty_list(self):
        with self._test_fixture_recording('test_Provider_when_calling_list_records_with_invalid_filter_should_be_empty_list'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            records = provider.list_records(DnsRecords.TXT_Record(None,'filter.thisdoesnotexist.{0}'.format(self.domain)))
            assert len(records) == 0

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_list_records_should_handle_record_sets(self):
        with self._test_fixture_recording('test_Provider_when_calling_list_records_should_handle_record_sets'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.listrecordset.{0}.".format(self.domain),'challengetoken1'))
            provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.listrecordset.{0}.".format(self.domain),'challengetoken2'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'_acme-challenge.listrecordset.{0}.'.format(self.domain)))
            assert len(records) == 2

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_delete_record_with_record_set_name_remove_all(self):
        with self._test_fixture_recording('test_Provider_when_calling_delete_record_with_record_set_name_remove_all'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.deleterecordset.{0}.".format(self.domain),'challengetoken1'))
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.deleterecordset.{0}.".format(self.domain),'challengetoken2'))

            assert provider.delete_record(DnsRecords.TXT_Record(None,'_acme-challenge.deleterecordset.{0}.'.format(self.domain)))
            records = provider.list_records(DnsRecords.TXT_Record(None,'_acme-challenge.deleterecordset.{0}.'.format(self.domain)))
            assert len(records) == 0

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_delete_record_with_record_set_by_content_should_leave_others_untouched(self):
        with self._test_fixture_recording('test_Provider_when_calling_delete_record_with_record_set_by_content_should_leave_others_untouched'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.deleterecordinset.{0}.".format(self.domain),'challengetoken1'))
            assert provider.create_record(DnsRecords.TXT_Record(None,"_acme-challenge.deleterecordinset.{0}.".format(self.domain),'challengetoken2'))

            assert provider.delete_record(DnsRecords.TXT_Record(None,'_acme-challenge.deleterecordinset.{0}.'.format(self.domain),'challengetoken1'))
            records = provider.list_records(DnsRecords.TXT_Record(None,'_acme-challenge.deleterecordinset.{0}.'.format(self.domain)))
            assert len(records) == 1

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_update_record_with_record_set_should_leave_others_untouched(self):
        with self._test_fixture_recording('test_Provider_when_calling_update_record_with_record_set_should_leave_others_untouched'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            name = "_acme-challenge.updaterecordinset.{0}.".format(self.domain)
            assert provider.create_record(DnsRecords.TXT_Record(None,name,'challengetoken1'))
            assert provider.create_record(DnsRecords.TXT_Record(None,name,'challengetoken2'))

            records = provider.list_records(DnsRecords.TXT_Record(None,name,'challengetoken1'))
            assert provider.update_record(DnsRecords.TXT_Record(id=records[0].id),DnsRecords.TXT_Record(content='newtoken1'))
            records = provider.list_records(DnsRecords.TXT_Record(None,name))
            assert len(records) == 2

    @pytest.mark.ext_suite_1
    def test_Provider_when_calling_update_record_with_record_set_by_content_should_leave_others_untouched(self):
        with self._test_fixture_recording('test_Provider_when_calling_update_record_with_record_set_by_content_should_leave_others_untouched'):
            provider = self.Provider(self._test_options(), self._test_engine_overrides())
            provider.authenticate()
            name = "_acme-challenge.updaterecordinsetbycontent.{0}.".format(self.domain)
            assert provider.create_record(DnsRecords.TXT_Record(None,name,'challengetoken1'))
            assert provider.create_record(DnsRecords.TXT_Record(None,name,'challengetoken2'))

            assert provider.update_record(DnsRecords.TXT_Record(None,name,'challengetoken1'),DnsRecords.TXT_Record(None,name,'newtoken1'))
            records = provider.list_records(DnsRecords.TXT_Record(None,name))
            assert len(records) == 2

        # Private helpers, mimicing the auth_* options provided by the Client
# http://stackoverflow.com/questions/6229073/how-to-make-a-python-dictionary-that-returns-key-for-keys-missing-from-the-dicti


    """
    This method lets you set options that are passed into the Provider. see lexicon/providers/base.py for a full list
    of options available. In general you should not need to override this method. Just override `self.domain`

    Any parameters that you expect to be passed to the provider via the cli, like --auth_username and --auth_token, will
    be present during the tests, with a 'placeholder_' prefix.

    options['auth_password'] == 'placeholder_auth_password'
    options['auth_username'] == 'placeholder_auth_username'
    options['unique_provider_option'] == 'placeholder_unique_provider_option'

    """
    def _test_options(self):
        cmd_options = SafeOptions()
        cmd_options['domain'] = self.domain
        cmd_options.update(env_auth_options(self.provider_name))
        return cmd_options

    """
    This method lets you override engine options. You must ensure the `fallbackFn` is defined, so your override might look like:

        def _test_engine_overrides(self):
            overrides = super(DnsmadeeasyProviderTests, self)._test_engine_overrides()
            overrides.update({'api_endpoint': 'http://api.sandbox.dnsmadeeasy.com/V2.0'})
            return overrides

    In general you should not need to override this method unless you need to override a provider setting only during testing.
    Like `api_endpoint`.
    """
    def _test_engine_overrides(self):
        overrides = {
            'fallbackFn': (lambda x: 'placeholder_' + x)
        }
        return overrides

    def _cassette_path(self, fixture_subpath):
        """
        A path customized for the provider's fixture.
        The default path is, for example:
            {provider}/IntegrationTests
        but if the test is a `provider_variant`, the path is customized to the variant:
            {provider}/{variant_name}-IntegrationTests
        """
        if self.provider_variant:
            return "{0}/{1}-{2}".format(self.provider_name, self.provider_variant, fixture_subpath)
        else:
            return "{0}/{1}".format(self.provider_name, fixture_subpath)

    # optional. used to identify the test variant, if any.
    provider_variant = None

    def _filter_headers(self):
        return []
    def _filter_query_parameters(self):
        return []
    def _filter_post_data_parameters(self):
        return []

    #http://preshing.com/20110920/the-python-with-statement-by-example/
    #https://jeffknupp.com/blog/2016/03/07/python-with-context-managers/
    @contextlib.contextmanager
    def _test_fixture_recording(self, test_name, recording_extension='yaml', recording_folder='IntegrationTests'):
        with provider_vcr.use_cassette(self._cassette_path('{0}/{1}.{2}'.format(recording_folder, test_name, recording_extension)),
                                       filter_headers=self._filter_headers(),
                                       filter_query_parameters=self._filter_query_parameters(),
                                       filter_post_data_parameters=self._filter_post_data_parameters()):
            yield
