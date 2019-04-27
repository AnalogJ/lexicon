# """Test for route53 implementation of the interface."""
# import unittest
# import pytest
# from lexicon.providers.route53 import Provider
# from lexicon.tests.providers.integration_tests import IntegrationTests, provider_vcr
#
# class Route53ProviderTests(unittest.TestCase, IntegrationTests):
#     """Route53 Proivder Tests."""
#
#     Provider = Provider
#     provider_name = 'route53'
#     domain = 'capsulecd.com'
#
#     def _filter_headers(self):
#         """Sensitive headers to be filtered."""
#         return ['Authorization']
#
#     def test_provider_authenticate_private_zone_only(self):
#         with provider_vcr.use_cassette(super(Route53ProviderTests, self)
#               ._cassette_path('IntegrationTests/test_provider_authenticate.yaml'),
#                   filter_headers=super(Route53ProviderTests, self)._filter_headers(),
#                   filter_query_parameters=super(Route53ProviderTests, self).
#                       ._filter_query_parameters(),
#                   filter_post_data_parameters=super(Route53ProviderTests, self)
#                       ._filter_post_data_parameters()):
#             options = super(Route53ProviderTests, self)._test_options()
#             options['private_zone'] = 'true'
#             provider = self.Provider(options, super(Route53ProviderTests, self)
#                           ._test_engine_overrides())
#             with pytest.raises(Exception):
#                 provider.authenticate()
#
#     def test_provider_authenticate_private_zone_false(self):
#         with provider_vcr.use_cassette(super(Route53ProviderTests, self)
#           ._cassette_path('IntegrationTests/test_provider_authenticate.yaml'),
#               filter_headers=super(Route53ProviderTests, self)._filter_headers(),
#               filter_query_parameters=super(Route53ProviderTests, self)
#                   ._filter_query_parameters(),
#               filter_post_data_parameters=super(Route53ProviderTests, self)
#                   ._filter_post_data_parameters()):
#             options = super(Route53ProviderTests, self)._test_options()
#             options['private_zone'] = 'false'
#             provider = self.Provider(options, super(Route53ProviderTests, self)
#                               ._test_engine_overrides())
#             provider.authenticate()
#             assert provider.domain_id is not None
#
#     @pytest.mark.skip(reason="route 53 dns records don't have ids")
#     def test_provider_when_calling_delete_record_by_identifier_should_remove_record(self):
#         return
#
#     # TODO: the following skipped suite and fixtures should be enabled
#     @pytest.mark.skip(reason="new test, missing recording")
#     def test_provider_when_calling_update_record_should_modify_record_name_specified(self):
#         return
#
#     @pytest.fixture(autouse=True)
#     def _skip_suite(self, request):  # pylint: disable=no-self-use
#         if request.node.get_closest_marker('ext_suite_1'):
#             pytest.skip('Skipping extended suite')
