from lexicon.providers.constellix import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Constellix does not currently have a sandbox and they enforce domain
# uniqueness across the service.  You'll need your own production credentials
# and a unique domain name if you want to run these tests natively.
class ConstellixProviderTests(TestCase, IntegrationTests):
    Provider = Provider
    provider_name = 'constellix'
    domain = 'example.org'

    def _filter_headers(self):
        return ['x-cnsdns-apiKey', 'x-cnsdns-hmac', 'x-cnsdns-requestDate']

