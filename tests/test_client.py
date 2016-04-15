import lexicon.client
import pytest
import os
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

def test_Client_parse_env_with_no_keys_should_do_nothing(monkeypatch):
    if os.environ.get('LEXICON_CLOUDFLARE_TOKEN'):
        monkeypatch.delenv('LEXICON_CLOUDFLARE_TOKEN')
    if os.environ.get('LEXICON_CLOUDFLARE_TOKEN'):
        monkeypatch.delenv('LEXICON_CLOUDFLARE_USERNAME')
    options = {
        'provider_name':'cloudflare',
        'action': 'list',
        'domain': 'www.example.com',
        'type': 'TXT'
    }
    client = lexicon.client.Client(options)


    assert client.provider_name == options['provider_name']
    assert client.action == options['action']
    assert client.options['domain'] == 'example.com'
    assert client.options['type'] == options['type']
    assert client.options.get('auth_token') == None
    assert client.options.get('auth_username') == None

def test_Client_parse_env_with_auth_keys(monkeypatch):
    monkeypatch.setenv('LEXICON_CLOUDFLARE_TOKEN','test-token')
    monkeypatch.setenv('LEXICON_CLOUDFLARE_USERNAME','test-username@example.com')
    options = {
        'provider_name':'cloudflare',
        'action': 'list',
        'domain': 'www.example.com',
        'type': 'TXT'
    }
    client = lexicon.client.Client(options)


    assert client.provider_name == options['provider_name']
    assert client.action == options['action']
    assert client.options['domain'] == 'example.com'
    assert client.options['type'] == options['type']
    assert client.options.get('auth_token') == 'test-token'
    assert client.options.get('auth_username') == 'test-username@example.com'



#TODO: add tests for Provider loading?