"""General pytest configuration for lexicon tests."""
import pytest

from lexicon import discovery


def pytest_addoption(parser):
    """Standard pytest hook invoked to add options to pytest CLI"""
    parser.addoption('--skip-providers-with-missing-deps', action='store_true',
                     help='Skip tests on providers with optional dependencies')


def pytest_runtest_setup(item):
    """Standard pytest hook invoked before each test execution"""
    try:
        skip_providers_with_optdeps = getattr(item.config.option, 'skip_providers_with_missing_deps')
    except AttributeError:
        pass
    else:
        print(skip_providers_with_optdeps)
        if skip_providers_with_optdeps:
            providers = discovery.find_providers()
            skip = [available for provider, available in providers.items()
                    if provider in item.parent.name.lower()]
            if skip and not skip[0]:
                pytest.xfail('Test skipped because --skip-providers-with-missing-deps '
                             'is set and provider has missing required dependencies.')
