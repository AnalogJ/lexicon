# Test for one implementation of the interface
from lexicon.providers.subreg import Provider
from integration_tests import IntegrationTests
from unittest import TestCase
import pytest

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class SubregProviderTests(TestCase, IntegrationTests):

    Provider = Provider
    provider_name = 'subreg'
    domain = 'oldium.net'
