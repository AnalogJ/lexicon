import lexicon.client
import pytest
import vcr
import os

# Configure VCR
provider_vcr = vcr.VCR(
        cassette_library_dir='tests/fixtures/cassettes',
        record_mode='new_episodes',
        decode_compressed_response=True
)



# https://stackoverflow.com/questions/26266481/pytest-reusable-tests-for-different-implementations-of-the-same-interface
# Single, reusable definition of tests for the interface. Authors of
# new implementations of the interface merely have to provide the test
# data, as class attributes of a class which inherits
# unittest.TestCase AND this class.
#
# Required test data:
# self.Provider must be set
# self.provider_name must be set
# self.domain must be set
# self._filter_headers can be defined to provide a list of sensitive headers
# self._filter_query_parameters can be defined to provide a list of sensitive parameter
class IntegrationTests():

    ###########################################################################
    # Provider.authenticate()
    ###########################################################################
    def test_Provider_authenticate(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_authenticate.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.domain_id is not None

    def test_Provider_authenticate_with_unmanaged_domain_should_fail(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_authenticate_with_unmanaged_domain_should_fail.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': 'thisisadomainidonotown.com',
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            with pytest.raises(StandardError):
                provider.authenticate()

    ###########################################################################
    # Provider.create_record()
    ###########################################################################
    def test_Provider_when_calling_create_record_for_A_with_valid_name_and_content(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_create_record_for_A_with_valid_name_and_content.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('A','localhost','127.0.0.1')

    def test_Provider_when_calling_create_record_for_CNAME_with_valid_name_and_content(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_create_record_for_CNAME_with_valid_name_and_content.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('CNAME','docs','docs.example.com')

    def test_Provider_when_calling_create_record_for_TXT_with_valid_name_and_content(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_create_record_for_TXT_with_valid_name_and_content.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT','_acme-challenge.test','challengetoken')

    def test_Provider_when_calling_create_record_for_TXT_with_full_name_and_content(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_create_record_for_TXT_with_full_name_and_content.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT',"_acme-challenge.full.{0}".format(self.domain),'challengetoken')

    def test_Provider_when_calling_create_record_for_TXT_with_fqdn_name_and_content(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_create_record_for_TXT_with_fqdn_name_and_content.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT',"_acme-challenge.fqdn.{0}.".format(self.domain),'challengetoken')

    ###########################################################################
    # Provider.list_records()
    ###########################################################################
    def test_Provider_when_calling_list_records_with_no_arguments_should_list_all(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_list_records_with_no_arguments_should_list_all.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert isinstance(provider.list_records(), list)

    def test_Provider_when_calling_list_records_with_name_filter_should_return_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_list_records_with_name_filter_should_return_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            provider.create_record('TXT','random.test','challengetoken')
            records = provider.list_records('TXT','random.test')
            assert len(records) == 1
            assert records[0]['content'] == 'challengetoken'
            assert records[0]['type'] == 'TXT'
            assert records[0]['name'] == 'random.test.{0}'.format(self.domain)

    def test_Provider_when_calling_list_records_with_full_name_filter_should_return_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_list_records_with_full_name_filter_should_return_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            provider.create_record('TXT','random.fulltest.{0}'.format(self.domain),'challengetoken')
            records = provider.list_records('TXT','random.fulltest.{0}'.format(self.domain))
            assert len(records) == 1
            assert records[0]['content'] == 'challengetoken'
            assert records[0]['type'] == 'TXT'
            assert records[0]['name'] == 'random.fulltest.{0}'.format(self.domain)

    def test_Provider_when_calling_list_records_with_fqdn_name_filter_should_return_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_list_records_with_fqdn_name_filter_should_return_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            provider.create_record('TXT','random.fqdntest.{0}.'.format(self.domain),'challengetoken')
            records = provider.list_records('TXT','random.fqdntest.{0}.'.format(self.domain))
            assert len(records) == 1
            assert records[0]['content'] == 'challengetoken'
            assert records[0]['type'] == 'TXT'
            assert records[0]['name'] == 'random.fqdntest.{0}'.format(self.domain)

    def test_Provider_when_calling_list_records_after_setting_ttl(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_list_records_after_setting_ttl.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token(),
                'ttl': 3600
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT',"ttl.fqdn.{0}.".format(self.domain),'ttlshouldbe3600')
            records = provider.list_records('TXT','ttl.fqdn.{0}'.format(self.domain))
            assert len(records) == 1
            assert str(records[0]['ttl']) == str(3600)

    @pytest.mark.skip(reason="not sure how to test empty list across multiple providers")
    def test_Provider_when_calling_list_records_should_return_empty_list_if_no_records_found(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_list_records_should_return_empty_list_if_no_records_found.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert isinstance(provider.list_records(), list)

    @pytest.mark.skip(reason="not sure how to test filtering across multiple providers")
    def test_Provider_when_calling_list_records_with_arguments_should_filter_list(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_list_records_with_arguments_should_filter_list.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert isinstance(provider.list_records(), list)

    ###########################################################################
    # Provider.update_record()
    ###########################################################################
    def test_Provider_when_calling_update_record_should_modify_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_update_record_should_modify_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT','orig.test','challengetoken')
            records = provider.list_records('TXT','orig.test')
            assert provider.update_record(records[0]['id'],'TXT','updated.test','challengetoken')

    def test_Provider_when_calling_update_record_with_full_name_should_modify_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_update_record_with_full_name_should_modify_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT','orig.testfull.{0}'.format(self.domain),'challengetoken')
            records = provider.list_records('TXT','orig.testfull.{0}'.format(self.domain))
            assert provider.update_record(records[0]['id'],'TXT','updated.testfull.{0}'.format(self.domain),'challengetoken')

    def test_Provider_when_calling_update_record_with_fqdn_name_should_modify_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_update_record_with_fqdn_name_should_modify_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT','orig.testfqdn.{0}.'.format(self.domain),'challengetoken')
            records = provider.list_records('TXT','orig.testfqdn.{0}.'.format(self.domain))
            assert provider.update_record(records[0]['id'],'TXT','updated.testfqdn.{0}.'.format(self.domain),'challengetoken')

    ###########################################################################
    # Provider.delete_record()
    ###########################################################################
    def test_Provider_when_calling_delete_record_by_identifier_should_remove_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_delete_record_by_identifier_should_remove_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT','delete.testid','challengetoken')
            records = provider.list_records('TXT','delete.testid')
            assert provider.delete_record(records[0]['id'])
            records = provider.list_records('TXT','delete.testid')
            assert len(records) == 0

    def test_Provider_when_calling_delete_record_by_filter_should_remove_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_delete_record_by_filter_should_remove_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT','delete.testfilt','challengetoken')
            assert provider.delete_record(None, 'TXT','delete.testfilt','challengetoken')
            records = provider.list_records('TXT','delete.testfilt')
            assert len(records) == 0

    def test_Provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_delete_record_by_filter_with_full_name_should_remove_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT', 'delete.testfull.{0}'.format(self.domain),'challengetoken')
            assert provider.delete_record(None, 'TXT', 'delete.testfull.{0}'.format(self.domain),'challengetoken')
            records = provider.list_records('TXT', 'delete.testfull.{0}'.format(self.domain))
            assert len(records) == 0

    def test_Provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record(self):
        with provider_vcr.use_cassette(self._cassette_path('IntegrationTests/test_Provider_when_calling_delete_record_by_filter_with_fqdn_name_should_remove_record.yaml'), filter_headers=self._filter_headers(), filter_query_parameters=self._filter_query_parameters(), filter_post_data_parameters=self._filter_post_data_parameters()):
            provider = self.Provider({
                'domain': self.domain,
                'auth_username': self._auth_username(),
                'auth_token': self._auth_token()
            }, self.provider_opts)
            provider.authenticate()
            assert provider.create_record('TXT', 'delete.testfqdn.{0}.'.format(self.domain),'challengetoken')
            assert provider.delete_record(None, 'TXT', 'delete.testfqdn.{0}.'.format(self.domain),'challengetoken')
            records = provider.list_records('TXT', 'delete.testfqdn.{0}.'.format(self.domain))
            assert len(records) == 0

# Private helpers, mimicing the auth_* options provided by the Client
    def _auth_username(self):
        return os.environ.get('LEXICON_{0}_USERNAME'.format(self.provider_name.upper())) or 'placeholder_auth_username'

    def _auth_password(self):
        return os.environ.get('LEXICON_{0}_PASSWORD'.format(self.provider_name.upper())) or 'placeholder_auth_password'

    def _auth_token(self):
        return os.environ.get('LEXICON_{0}_TOKEN'.format(self.provider_name.upper())) or 'placeholder_auth_token'

    def _cassette_path(self, fixture_subpath):
        return "{0}/{1}".format(self.provider_name, fixture_subpath)

    def _filter_headers(self):
        return []
    def _filter_query_parameters(self):
        return []
    def _filter_post_data_parameters(self):
        return []

    provider_opts = {}