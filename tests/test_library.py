"""
This unit test suite ensures that the lexicon client works correctly when used as a library.
In particular:
    - relevant provider should be resolved correctly from config,
    - config should be passed correctly to provider,
    - relevant provider method should be invoked for a given config.
"""

import importlib

import pytest

from lexicon.config import ConfigResolver
from lexicon.exceptions import ProviderNotAvailableError


@pytest.fixture
def lexicon_client():
    """Return the lexicon_client"""
    return importlib.import_module("lexicon.client")


def test_unknown_provider_raises_error_on_instantiation(lexicon_client):
    with pytest.raises(ProviderNotAvailableError):
        lexicon_client.Client(
            ConfigResolver().with_dict(
                {
                    "provider_name": "unknownprovider",
                    "domain": "example.com",
                }
            )
        )


def test_missing_required_client_config_parameter_raises_error_on_instantiation(
    lexicon_client, mock_provider
):
    with pytest.raises(AttributeError):
        lexicon_client.Client(
            ConfigResolver().with_dict(
                {
                    "provider_name": "fakeprovider",
                    "no-domain": "example.com",
                }
            )
        )
    with pytest.raises(AttributeError):
        lexicon_client.Client(
            ConfigResolver().with_dict(
                {
                    "no-provider_name": "fakeprovider",
                    "domain": "example.com",
                }
            )
        )


def test_missing_required_client_config_parameter_raises_error_on_execute(
    lexicon_client, mock_provider
):
    with pytest.raises(AttributeError):
        lexicon_client.Client(
            ConfigResolver().with_dict(
                {
                    "no-action": "list",
                    "provider_name": "fakeprovider",
                    "domain": "example.com",
                    "type": "TXT",
                }
            )
        ).execute()
    with pytest.raises(AttributeError):
        lexicon_client.Client(
            ConfigResolver().with_dict(
                {
                    "action": "list",
                    "provider_name": "fakeprovider",
                    "domain": "example.com",
                    "no-type": "TXT",
                }
            )
        ).execute()


def test_missing_optional_client_config_parameter_does_not_raise_error_on_execute(
    lexicon_client, mock_provider
):
    lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "action": "list",
                "provider_name": "fakeprovider",
                "domain": "example.com",
                "type": "TXT",
                "no-name": "fake",
                "no-content": "fake",
            }
        )
    ).execute()


def test_list_action_is_correctly_handled_by_provider_on_execute(
    capsys, lexicon_client, mock_provider
):
    client = lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "action": "list",
                "provider_name": "fakeprovider",
                "domain": "example.com",
                "type": "TXT",
                "name": "fake",
                "content": "fake-content",
            }
        )
    )
    results = client.execute()

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "list"
    assert results["domain"] == "example.com"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"


def test_list_action_is_correctly_handled_by_provider_on_context_manager(
    capsys, lexicon_client, mock_provider
):
    with lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "provider_name": "fakeprovider",
                "domain": "example.com",
            }
        )
    ) as client:
        results = client.list_records("TXT", "fake", "fake-content")

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "list"
    assert results["domain"] == "example.com"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"


def test_create_action_is_correctly_handled_by_provider_on_execute(
    capsys, lexicon_client, mock_provider
):
    client = lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "action": "create",
                "provider_name": "fakeprovider",
                "domain": "example.com",
                "type": "TXT",
                "name": "fake",
                "content": "fake-content",
            }
        )
    )
    results = client.execute()

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "create"
    assert results["domain"] == "example.com"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"


def test_create_action_is_correctly_handled_by_provider_on_context_manager(
    capsys, lexicon_client, mock_provider
):
    with lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "provider_name": "fakeprovider",
                "domain": "example.com",
            }
        )
    ) as client:
        results = client.create_record("TXT", "fake", "fake-content")

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "create"
    assert results["domain"] == "example.com"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"


def test_update_action_is_correctly_handled_by_provider_on_execute(
    capsys, lexicon_client, mock_provider
):
    client = lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "action": "update",
                "provider_name": "fakeprovider",
                "domain": "example.com",
                "identifier": "fake-id",
                "type": "TXT",
                "name": "fake",
                "content": "fake-content",
            }
        )
    )
    results = client.execute()

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "update"
    assert results["domain"] == "example.com"
    assert results["identifier"] == "fake-id"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"


def test_update_action_is_correctly_handled_by_provider_on_context_manager(
    capsys, lexicon_client, mock_provider
):
    with lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "provider_name": "fakeprovider",
                "domain": "example.com",
            }
        )
    ) as client:
        results = client.update_record("fake-id", "TXT", "fake", "fake-content")

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "update"
    assert results["domain"] == "example.com"
    assert results["identifier"] == "fake-id"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"


def test_delete_action_is_correctly_handled_by_provider_on_execute(
    capsys, lexicon_client, mock_provider
):
    client = lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "action": "delete",
                "provider_name": "fakeprovider",
                "domain": "example.com",
                "identifier": "fake-id",
                "type": "TXT",
                "name": "fake",
                "content": "fake-content",
            }
        )
    )
    results = client.execute()

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "delete"
    assert results["domain"] == "example.com"
    assert results["identifier"] == "fake-id"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"


def test_delete_action_is_correctly_handled_by_provider_on_context_manager(
    capsys, lexicon_client, mock_provider
):
    with lexicon_client.Client(
        ConfigResolver().with_dict(
            {
                "provider_name": "fakeprovider",
                "domain": "example.com",
            }
        )
    ) as client:
        results = client.delete_record("fake-id", "TXT", "fake", "fake-content")

    out, _ = capsys.readouterr()

    assert "Authenticate action" in out
    assert results["action"] == "delete"
    assert results["domain"] == "example.com"
    assert results["identifier"] == "fake-id"
    assert results["type"] == "TXT"
    assert results["name"] == "fake"
    assert results["content"] == "fake-content"
