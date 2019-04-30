"""test module for aliyun provider"""

# Test for one implementation of the interface
from unittest import TestCase
from lexicon.tests.providers.integration_tests import IntegrationTests

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class AliyunProviderTests(TestCase, IntegrationTests):
    """Integration tests for Foo provider"""
    provider_name = 'aliyun'
    domain = 'mean.space'

    """filter access key id"""
    def _filter_query_parameters(self):
        return ['AccessKeyId', 'Signature', 'SignatureNonce', 'Timestamp']
