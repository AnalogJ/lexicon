"""
This unit test suite ensures that the lexicon client works correctly when used as a library.
In particular:
    - relevant provider should be resolved correctly from config,
    - config should be passed correctly to provider,
    - relevant provider method should be invoked for a given config.
"""
# pylint: disable=missing-docstring,redefined-outer-name
from __future__ import absolute_import, print_function
import importlib
import pkgutil
from types import ModuleType
import contextlib

import pytest
import mock

from lexicon.client import ProviderNotAvailableError
from lexicon.providers.base import Provider as BaseProvider


class Provider(BaseProvider):
    """
    Fake provider to simulate the provider resolution from configuration,
    and to have excution traces when lexicon client is invoked
    """
    def _authenticate(self):
        print('Authenticate action')

    def _create_record(self, rtype, name, content):
        return {'action': 'create', 'domain': self.domain,
                'type': rtype, 'name': name, 'content': content}

    def _list_records(self, rtype=None, name=None, content=None):
        return {'action': 'list', 'domain': self.domain,
                'type': rtype, 'name': name, 'content': content}

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        return {'action': 'update', 'domain': self.domain, 'identifier': identifier,
                'type': rtype, 'name': name, 'content': content}

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        return {'action': 'delete', 'domain': self.domain, 'identifier': identifier,
                'type': rtype, 'name': name, 'content': content}

    def _request(self, action='GET', url='/', data=None, query_params=None):
        # Not use for tests
        pass


@contextlib.contextmanager
def mock_fake_provider():
    """
    Create a fake provider module, and mock relevant
    functions to make it appear as a real module.
    """
    original_iter = pkgutil.iter_modules
    original_import = importlib.import_module
    with mock.patch('lexicon.discovery.pkgutil.iter_modules') as mock_iter,\
            mock.patch('lexicon.client.importlib.import_module') as mock_import:
        def return_iter(path):
            """
            This will include an adhoc fakeprovider module
            to the normal return of pkgutil.iter_modules.
            """
            modules = list(original_iter(path))
            modules.append((None, 'fakeprovider', None))
            return modules
        mock_iter.side_effect = return_iter

        def return_import(module_name):
            """
            This will return a adhoc fakeprovider module if necessary,
            or fallback to the normal return of importlib.import_module.
            """
            if module_name == 'lexicon.providers.fakeprovider':
                module = ModuleType('lexicon.providers.fakeprovider')
                setattr(module, 'Provider', Provider)
                return module
            return original_import(module_name)
        mock_import.side_effect = return_import

        yield


@pytest.fixture
def lexicon_client():
    """Return the lexicon_client"""
    return importlib.import_module('lexicon.client')


@pytest.fixture(autouse=True)
def fake_provider():
    """Activate the fake_provider mock"""
    with mock_fake_provider():
        yield


def test_unknown_provider_raises_error(lexicon_client):
    with pytest.raises(ProviderNotAvailableError):
        lexicon_client.Client({'action': 'list', 'provider_name': 'unknownprovider',
                               'domain': 'example.com', 'type': 'TXT',
                               'name': 'fake', 'content': 'fake'})


def test_missing_required_client_config_parameter_raises_error(lexicon_client):
    with pytest.raises(AttributeError):
        lexicon_client.Client({'no-action': 'list', 'provider_name': 'fakeprovider',
                               'domain': 'example.com', 'type': 'TXT',
                               'name': 'fake', 'content': 'fake'})
    with pytest.raises(AttributeError):
        lexicon_client.Client({'action': 'list', 'no-provider_name': 'fakeprovider',
                               'domain': 'example.com', 'type': 'TXT',
                               'name': 'fake', 'content': 'fake'})
    with pytest.raises(AttributeError):
        lexicon_client.Client({'action': 'list', 'provider_name': 'fakeprovider',
                               'no-domain': 'example.com', 'type': 'TXT',
                               'name': 'fake', 'content': 'fake'})
    with pytest.raises(AttributeError):
        lexicon_client.Client({'action': 'list', 'provider_name': 'fakeprovider',
                               'domain': 'example.com', 'no-type': 'TXT',
                               'name': 'fake', 'content': 'fake'})


def test_missing_optional_client_config_parameter_does_not_raise_error(lexicon_client):
    lexicon_client.Client({'action': 'list', 'provider_name': 'fakeprovider',
                           'domain': 'example.com', 'type': 'TXT',
                           'no-name': 'fake', 'no-content': 'fake'})


def test_list_action_is_correctly_handled_by_provider(capsys, lexicon_client):
    client = lexicon_client.Client({'action': 'list', 'provider_name': 'fakeprovider',
                                    'domain': 'example.com', 'type': 'TXT',
                                    'name': 'fake', 'content': 'fake-content'})
    results = client.execute()

    out, _ = capsys.readouterr()

    assert 'Authenticate action' in out
    assert results['action'] == 'list'
    assert results['domain'] == 'example.com'
    assert results['type'] == 'TXT'
    assert results['name'] == 'fake'
    assert results['content'] == 'fake-content'


def test_create_action_is_correctly_handled_by_provider(capsys, lexicon_client):
    client = lexicon_client.Client({'action': 'create', 'provider_name': 'fakeprovider',
                                    'domain': 'example.com', 'type': 'TXT',
                                    'name': 'fake', 'content': 'fake-content'})
    results = client.execute()

    out, _ = capsys.readouterr()

    assert 'Authenticate action' in out
    assert results['action'] == 'create'
    assert results['domain'] == 'example.com'
    assert results['type'] == 'TXT'
    assert results['name'] == 'fake'
    assert results['content'] == 'fake-content'


def test_update_action_is_correctly_handled_by_provider(capsys, lexicon_client):
    client = lexicon_client.Client({'action': 'update', 'provider_name': 'fakeprovider',
                                    'domain': 'example.com', 'identifier': 'fake-id',
                                    'type': 'TXT', 'name': 'fake', 'content': 'fake-content'})
    results = client.execute()

    out, _ = capsys.readouterr()

    assert 'Authenticate action' in out
    assert results['action'] == 'update'
    assert results['domain'] == 'example.com'
    assert results['identifier'] == 'fake-id'
    assert results['type'] == 'TXT'
    assert results['name'] == 'fake'
    assert results['content'] == 'fake-content'


def test_delete_action_is_correctly_handled_by_provider(capsys, lexicon_client):
    client = lexicon_client.Client({'action': 'delete', 'provider_name': 'fakeprovider',
                                    'domain': 'example.com', 'identifier': 'fake-id',
                                    'type': 'TXT', 'name': 'fake', 'content': 'fake-content'})
    results = client.execute()

    out, _ = capsys.readouterr()

    assert 'Authenticate action' in out
    assert results['action'] == 'delete'
    assert results['domain'] == 'example.com'
    assert results['identifier'] == 'fake-id'
    assert results['type'] == 'TXT'
    assert results['name'] == 'fake'
    assert results['content'] == 'fake-content'
