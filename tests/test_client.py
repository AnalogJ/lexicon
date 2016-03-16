import lexicon.client
import pytest

def test_Client_init():
    options = {
        'provider_name':'base',
        'action': 'list',
        'domain': 'example.com',
        'type': 'TXT'
    }
    client = lexicon.client.Client(options)

    assert client.provider_name == options['provider_name']
    assert client.action == options['action']
    assert client.options['domain'] == options['domain']
    assert client.options['type'] == options['type']

def test_Client_init_when_domain_includes_subdomain_should_strip():
    options = {
        'provider_name':'base',
        'action': 'list',
        'domain': 'www.example.com',
        'type': 'TXT'
    }
    client = lexicon.client.Client(options)

    assert client.provider_name == options['provider_name']
    assert client.action == options['action']
    assert client.options['domain'] == 'example.com'
    assert client.options['type'] == options['type']


def test_Client_init_when_missing_provider_should_fail():
    options = {
        'action': 'list',
        'domain': 'example.com',
        'type': 'TXT'
    }
    with pytest.raises(AttributeError):
        lexicon.client.Client(options)

def test_Client_init_when_missing_action_should_fail():
    options = {
        'provider_name':'base',
        'domain': 'example.com',
        'type': 'TXT'
    }
    with pytest.raises(AttributeError):
        lexicon.client.Client(options)

def test_Client_init_when_missing_domain_should_fail():
    options = {
        'provider_name':'base',
        'action': 'list',
        'type': 'TXT'
    }
    with pytest.raises(AttributeError):
        lexicon.client.Client(options)

def test_Client_init_when_missing_type_should_fail():
    options = {
        'provider_name':'base',
        'action': 'list',
        'domain': 'example.com',
    }
    with pytest.raises(AttributeError):
        lexicon.client.Client(options)

#TODO: add tests for Provider loading?