"""General pytest configuration for lexicon tests."""
import pytest
import pkg_resources

LEXICON_DISTRIBUTION = pkg_resources.require('dns-lexicon')[0]
PROVIDERS_WITH_OPTIONALS = [provider for provider in LEXICON_DISTRIBUTION.extras
                            if provider not in ('dev', 'full')]


def pytest_addoption(parser):
    """Standard pytest hook invoked to add options to pytest CLI"""
    parser.addoption('--skip-providers-with-optdeps', action='store_true',
                     help='Skip tests on providers with optional dependencies')


def pytest_runtest_setup(item):
    """Standard pytest hook invoked before each test execution"""
    try:
        skip_providers_with_optdeps = getattr(item.config.option, 'skip_providers_with_optdeps')
    except AttributeError:
        pass
    else:
        skip = [provider for provider in PROVIDERS_WITH_OPTIONALS
                if provider in item.parent.name.lower()]
        if skip_providers_with_optdeps and skip:
            pytest.skip('Test skipped because --skip-providers-with-optdeps '
                        'is set and provider is marked as having optional dependencies.')
