"""Integration tests for Google Cloud DNS"""
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTests


# All data in the following service_account base64-encoded file have been invalidated
SERVICE_ACCOUNT_INFO_BASE64 = 'ew0KICAidHlwZSI6ICJzZXJ2aWNlX2FjY291bnQiLA0KICAicHJvamVjdF9pZCI6ICJuYW1lZC1hcmNod2F5LTIwOTQxOCIsDQogICJwcml2YXRlX2tleV9pZCI6ICIyMmI1ZDAyZWM2MDA4OTQ3OTg2NzljYzlhYzdiNDJlZGExMDBiODg2IiwNCiAgInByaXZhdGVfa2V5IjogIi0tLS0tQkVHSU4gUFJJVkFURSBLRVktLS0tLVxuTUlJRXZBSUJBREFOQmdrcWhraUc5dzBCQVFFRkFBU0NCS1l3Z2dTaUFnRUFBb0lCQVFEQU9ZUUdOcTZsN2tCT1xuNDMwQjZPWExtQzZUcEVuRDdzL2pqZFI0UFhFSnZkenBkQm5OT3h5cktXcm9Sa0ZheFJCY1BNMUJBODJsMVBkZFxuWUtYdWkrTmpKUVdqc3hoTkNNSGN5Uzl5T3NDYmZvMWxrRFpWU3dQRitXbnB3aDMydTVGSGFSUlpacnVaM29FNFxucjUrbzd4NS9NWWl2RlBiZlZSeEZNNi9lYkgwNFZ6NytjUms0ZjdZQktZNXYzTHFob2JnVW5nZGlHd29BTEs2TVxuS1hDKzF6SXRTVGdETHdCblRTU0xvSVRVNXNhZEY0L2dqVmNKTkxNM1RaQmU0djV3MGtPOU9ieTFsOVZVcHh3ZFxuZDlyRHBFR2o0Y3FnWWZ3QkZZai9wNE13L1p1Rksra2VlZDBrQjgyZEQ0M21jeDk5WWptTXBmd2FOWEp3L09XblxuanRnWWhyWk5BZ01CQUFFQ2dnRUFDd3JTeVh1WExVdUNNTFh6UHFxWEZzcTdkRHBHRFlZWXRhRDJZV0RnTHpmVFxucXFxRGQrMXJJRzc4NS9Kdk95eGlXL1lYTVdLclM5a3Z5NUtyZlloV0srSWEwSlJQYzA5ck9ZaHFIQlVCYnYxR1xuV0p6LzdnYms1TmpHeTRtZDZJaE9XR3lTSVcrY0c4THpKK000MS83Q2dQcUN1RklMTzNtYmFlTkYrVkJBb2oyUlxuUzhGZjlQUWRCejdGUFF5bENsODJmeUVRN2I0eGhwMGtoNEdiZ0JHMTJKc1FMQlFPUC9nK1lJdkp0SmVrVDJOWlxuckYxVXZybWZRc1N2UFdaYXFkVW81MGhiVEQyZUdvTlM4R2pGcFh5WTc5SXFZTmh3MTVaYlNVQXVoWGVndWRKelxueWtRYUgyUUY5am9YTjV6TkNJalhxL1U3aUhCK2QxOGRwcEkxOEFoWUVRS0JnUURuVzJPWGNsVUwxbVBSdE5XV1xuLzJxUzJidWpBVUlmR1pERjhURk0yZGJ0RFk4L04rejVkQWNMYndIWTNEYmt5djBVZlRRY0hlaXhyRFBlZkwrTlxudCtnK3BwWG1rWVVYbHNUZ0p0THRrZmlGWU5IbHJKeGNESVF5KzFPSzVlYjdCVUxsZEFzOXozT1FUOXVQS0U3SVxuWDNscDF6eXZzc0tQcjhGSXF6K2puYlgzVVFLQmdRRFVzeEpzSlI5dDJDckVwZEh3MGZOYjhqUzMzRDJXME44dlxuSUp6SWFCYlZvbjYrSGpmc2grZE05VitBR21RYWg2ODFoWE1xRmVQemdreFdNcHZ1UEhRZ2tHUlIyOTBpWjlwSVxuRmVBaUVCUmtNUWtNQUFIVFN2YlZXdWtCY2pIZFQ3UWpKc3NCd24xbTJWem1nUlBTMWVnZUNsQ1pMalZuWlhxM1xuQ0plNXZkeElQUUtCZ0FZREN2QjVpUm80cFBsakVKWE81MDhQbDEraC9iemZKakx1bEpCaHJNTVdNaDI3YjA0QVxuSk5xNE5MMFU0OXhJSmhGdE8zaHJrb3RqWlNtbjVqWmhqQWhzdmNKekQ1bFFVcWRjZXVpdmZWekI2bEprak4rYlxuZDZmM2ZmRkREaUNCdjM1RTZMSGZmU3BIMlBXOFgyZTNpMmtqcmJFSEhTVXN0UUlWYVI3d1R6VXhBb0dBWG9JeVxuN1ZxUlhIMXdnM0FxbUpheFMybVRneDZaUHlvUUFTQzhpVSsyMWJZZUd0dlNmWWJsZjR5SG9xUVhWckp6WjVTa1xuVjA3aXVwQnEydUloNXZsMW9BS0lrTmJncXlqNkZJMmp5WDdia0trNUc5dms4NzJiYjdHMVZxOG0rTzh4VzIwaFxuUnVia1VZN0RlS2hoNW95bFZyTytuRkdyNlFWdVFXWFFCUGdYcVFFQ2dZQXU5dkw0aGhvb2pjS1lFdXdhUDA1bFxuNHVGVGVoZEpSQTRXdU9TK1RYeG9WM1VXWUI3cDBjdnNUaWs3N1BITy9rU1pKQzZDMWZpTEM1aG5NT05FaFg0OVxuZCtFbkNaL2dyL3pGQ1BoV0VwbmZ4WFF0WkpWRVBnQW1CK01tcDNQSXdlWG9jQkhpMFFza1VJVzJrRGhtdTdmcFxuMEg1M1FadlpHaTd6MktuUnovcDRJdz09XG4tLS0tLUVORCBQUklWQVRFIEtFWS0tLS0tXG4iLA0KICAiY2xpZW50X2VtYWlsIjogInNlcnZpY2UtZG5zQG5hbWVkLWFyY2h3YXktMjA5NDE4LmlhbS5nc2VydmljZWFjY291bnQuY29tIiwNCiAgImNsaWVudF9pZCI6ICIxMTY2MDYxNjkyODU0MDQyMDUxNTAiLA0KICAiYXV0aF91cmkiOiAiaHR0cHM6Ly9hY2NvdW50cy5nb29nbGUuY29tL28vb2F1dGgyL2F1dGgiLA0KICAidG9rZW5fdXJpIjogImh0dHBzOi8vYWNjb3VudHMuZ29vZ2xlLmNvbS9vL29hdXRoMi90b2tlbiIsDQogICJhdXRoX3Byb3ZpZGVyX3g1MDlfY2VydF91cmwiOiAiaHR0cHM6Ly93d3cuZ29vZ2xlYXBpcy5jb20vb2F1dGgyL3YxL2NlcnRzIiwNCiAgImNsaWVudF94NTA5X2NlcnRfdXJsIjogImh0dHBzOi8vd3d3Lmdvb2dsZWFwaXMuY29tL3JvYm90L3YxL21ldGFkYXRhL3g1MDkvc2VydmljZS1kbnMlNDBuYW1lZC1hcmNod2F5LTIwOTQxOC5pYW0uZ3NlcnZpY2VhY2NvdW50LmNvbSINCn0NCg=='  # pylint: disable=line-too-long

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests


class GoogleCloudDnsTests(TestCase, IntegrationTests):
    """TestCase for Google Cloud DNS"""
    provider_name = 'googleclouddns'
    domain = 'fullm3tal.tk'

    def _filter_headers(self):
        return ['Authorization']

    # WARNING !
    # The body parameters 'access_token' and 'assertion'
    # must be removed from the authentication phase.
    # However the body is not JSON encoded, so _filter_headers
    # and _filter_query_parameters methods are of no use.
    # You will need to replace manually theses parameters from the cassettes by placeholders.
    # Typically,
    #   - for assertion with regex replace: assertion=[\w-%]+\.[\w-%]+\.[\w-%]+
    #                                                   => assertion=assertion_placeholder
    #   - for access_token with regex replace: ya29\.c\.[\w-]+
    #                                                   => access_token_placeholder
    #
    # Override _test_options to call env_auth_options and then import auth config from env variables
    def _test_parameters_overrides(self):
        return {'auth_service_account_info': 'base64::{0}'.format(SERVICE_ACCOUNT_INFO_BASE64)}
