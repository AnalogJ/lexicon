# Test for one implementation of the interface
from lexicon.tests.providers.integration_tests import IntegrationTests
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class AliyunProviderTests(TestCase, IntegrationTests):
    """Integration tests for Foo provider"""
    provider_name = 'aliyun'
    domain = 'mean.space'