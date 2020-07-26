"""test module for aliyun provider"""

# Test for one implementation of the interface
from unittest import TestCase

from lexicon.tests.providers.integration_tests import IntegrationTestsV2


# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class AliyunProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Foo provider"""

    provider_name = "aliyun"
    domain = "mean.space"

    def _filter_query_parameters(self):
        """filter access key id && secret info"""
        return [
            ("AccessKeyId", "DUMMY_KEY_ID"),
            ("Signature", "DUMMY_SIGNATURE"),
            ("SignatureNonce", "DUMMY_SIGNATURE_NONCE"),
            ("Timestamp", "DUMMY_TIMESTAMP"),
        ]
