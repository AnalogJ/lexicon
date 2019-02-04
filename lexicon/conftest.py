import pytest


def pytest_addoption(parser):
    parser.addoption('--skip-providers-with-optdeps', action='store_true',
                     help='Skip tests on providers with optional dependencies')


def pytest_runtest_setup(item):
    try:
        skip_providers_with_optdeps = getattr(item.config.option, 'skip_providers_with_optdeps')
    except AttributeError:
        pass
    else:
        if skip_providers_with_optdeps and item.parent.get_closest_marker('provider_with_optdeps'):
            pytest.skip('Test skipped because --skip-providers-with-optdeps '
                        'is set and provider is marked as having optional dependencies.')
