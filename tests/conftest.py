import importlib
import pkgutil
from argparse import ArgumentParser
from re import Pattern
from types import ModuleType
from typing import List, Union, cast
from unittest import mock

import pytest


def pytest_addoption(parser):
    """Standard pytest hook invoked to add options to pytest CLI"""
    parser.addoption(
        "--xfail-providers-with-missing-deps",
        action="store_true",
        help="Skip tests on providers with optional dependencies",
    )


def pytest_runtest_setup(item):
    """Standard pytest hook invoked before each test execution"""
    try:
        skip_providers_with_optdeps = getattr(
            item.config.option, "xfail_providers_with_missing_deps"
        )
    except AttributeError:
        pass
    else:
        if skip_providers_with_optdeps:
            from lexicon.discovery import find_providers

            providers = find_providers()
            skip = [
                available
                for provider, available in providers.items()
                if provider in item.parent.name.lower()
            ]
            if skip and not skip[0]:
                pytest.xfail(
                    "Test expected to fail because --skip-providers-with-missing-deps "
                    "is set and provider has missing required dependencies."
                )


@pytest.fixture(scope="session")
def mock_provider():
    """
    Create a fake provider module, and mock relevant
    functions to make it appear as a real module.
    """
    from lexicon.providers.base import Provider as BaseProvider

    class Provider(BaseProvider):
        """
        Fake provider to simulate the provider resolution from configuration,
        and to have execution traces when lexicon client is invoked
        """

        @staticmethod
        def get_nameservers() -> Union[List[str], List[Pattern]]:
            return cast(List[str], [])

        @staticmethod
        def configure_parser(parser: ArgumentParser) -> None:
            pass

        def authenticate(self):
            print("Authenticate action")

        def create_record(self, rtype, name, content):
            return {
                "action": "create",
                "domain": self.domain,
                "type": rtype,
                "name": name,
                "content": content,
            }

        def list_records(self, rtype=None, name=None, content=None):
            return {
                "action": "list",
                "domain": self.domain,
                "type": rtype,
                "name": name,
                "content": content,
            }

        def update_record(self, identifier, rtype=None, name=None, content=None):
            return {
                "action": "update",
                "domain": self.domain,
                "identifier": identifier,
                "type": rtype,
                "name": name,
                "content": content,
            }

        def delete_record(self, identifier=None, rtype=None, name=None, content=None):
            return {
                "action": "delete",
                "domain": self.domain,
                "identifier": identifier,
                "type": rtype,
                "name": name,
                "content": content,
            }

        def _request(self, action="GET", url="/", data=None, query_params=None):
            # Not use for tests
            pass

    original_iter = pkgutil.iter_modules
    original_import = importlib.import_module
    with mock.patch("lexicon.discovery.pkgutil.iter_modules") as mock_iter, mock.patch(
        "lexicon.client.importlib.import_module"
    ) as mock_import:

        def return_iter(path):
            """
            This will include an adhoc fakeprovider module
            to the normal return of pkgutil.iter_modules.
            """
            modules = list(original_iter(path))
            modules.append((None, "fakeprovider", None))
            return modules

        mock_iter.side_effect = return_iter

        def return_import(module_name):
            """
            This will return a adhoc fakeprovider module if necessary,
            or fallback to the normal return of importlib.import_module.
            """
            if module_name == "lexicon.providers.fakeprovider":
                module = ModuleType("lexicon.providers.fakeprovider")
                setattr(module, "Provider", Provider)
                return module
            return original_import(module_name)

        mock_import.side_effect = return_import

        yield
