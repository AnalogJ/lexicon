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

def test_Client_init_with_delegated_domain_name():
    options = {
        'provider_name':'base',
        'action': 'list',
        'domain': 'www.sub.example.com',
        'delegated': 'sub',
        'type': 'TXT'
    }
    client = lexicon.client.Client(options)

    assert client.provider_name == options['provider_name']
    assert client.action == options['action']
    assert client.options['domain'] == "sub.example.com"
    assert client.options['type'] == options['type']

def test_Client_init_with_delegated_domain_fqdn():
    options = {
        'provider_name':'base',
        'action': 'list',
        'domain': 'www.sub.example.com',
        'delegated': 'sub.example.com',
        'type': 'TXT'
    }
    client = lexicon.client.Client(options)

    assert client.provider_name == options['provider_name']
    assert client.action == options['action']
    assert client.options['domain'] == "sub.example.com"
    assert client.options['type'] == options['type']

def test_Client_init_with_same_delegated_domain_fqdn():
    options = {
        'provider_name':'base',
        'action': 'list',
        'domain': 'www.example.com',
        'delegated': 'example.com',
        'type': 'TXT'
    }
    client = lexicon.client.Client(options)

    assert client.provider_name == options['provider_name']
    assert client.action == options['action']
    assert client.options['domain'] == "example.com"
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
    if os.environ.get('LEXICON_CLOUDFLARE_USERNAME'):
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

def test_Client_normalize_one_content_arg():
    options = {
        'provider_name':'base',
        'action': 'create',
        'domain': 'example.com',
        'type': 'A',
        'content': ['127.0.0.1']
    }
    client = lexicon.client.Client(options)

    assert type(client.options['content']) is str
    assert client.options['content'] == '127.0.0.1'

def test_Client_normalize_multi_content_args():
    options = {
        'provider_name':'base',
        'action': 'create',
        'domain': 'example.com',
        'type': 'A',
        'content': ['127.0.0.1', '127.0.0.2']
    }
    client = lexicon.client.Client(options)

    assert type(client.options['content']) is list
    assert len(client.options['content']) == 2
    assert client.options['content'][0] == '127.0.0.1'
    assert client.options['content'][1] == '127.0.0.2'

#TODO: add tests for Provider loading?
