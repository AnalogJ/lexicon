from lexicon.common.options_handler import *

def test_env_auth_options_reads_only_specified_env(monkeypatch):
    monkeypatch.setenv('LEXICON_FOO_USERNAME','test_username')
    env_auth_options('foo')['auth_username'] == 'test_username'


def test_SafeOptions_update_shouldnt_override_when_None():
    options = SafeOptions()
    options['test'] = 'test'
    assert options['test'] == 'test'
    options.update({'test':None})
    assert options['test'] == 'test'

def test_SafeOptions_update_should_handle_empty_update():
    options = SafeOptions()
    options['test'] = 'test'
    assert options['test'] == 'test'
    options.update({})
    assert options['test'] == 'test'

def test_OptionsWithFallback_returns_none_when_no_fallbackFn_set():
    options = SafeOptionsWithFallback()
    assert options['test'] == None

def test_OptionsWithFallback_with_only_data_should_return():
    options = SafeOptionsWithFallback({'foo': 'bar'})
    assert options['test'] == None
    assert options['foo'] == 'bar'


def test_OptionsWithFallback_returns_placeholder_when_fallbackFn_set():
    options = SafeOptionsWithFallback({}, lambda x: 'placeholder_' + x)
    options['exists'] = 'test_value'
    assert options['test_key1'] == 'placeholder_test_key1'
    assert options.get('test_key2') == 'placeholder_test_key2'
    assert options['exists'] == 'test_value'
    assert options.get('exists') == 'test_value'


def test_OptionsWithFallback_chain(monkeypatch):
    base_options = SafeOptionsWithFallback({}, lambda x: 'placeholder_' + x)
    base_options['test1'] = 'base'
    base_options['test2'] = 'base'
    base_options['test3'] = 'base'
    base_options['auth_test3'] = 'base'
    base_options['auth_test4'] = 'base'

    provider_options = SafeOptions()
    provider_options['test2'] = 'provider'
    provider_options['test3'] = 'provider'
    provider_options['auth_test3'] = 'provider'
    provider_options['auth_test4'] = 'provider'


    monkeypatch.setenv('LEXICON_FOO_TEST3','env')
    monkeypatch.setenv('LEXICON_FOO_TEST4','env')
    env_options = env_auth_options('foo')

    cli_options = SafeOptions()
    cli_options['auth_test4'] = 'cli'


    #merge them together
    base_options.update(provider_options)
    base_options.update(env_options)
    base_options.update(cli_options)


    assert base_options['test0'] == 'placeholder_test0'
    assert base_options['test1'] == 'base'
    assert base_options['test2'] == 'provider'
    assert base_options['test3'] == 'provider'
    assert base_options['auth_test3'] == 'env'
    assert base_options['auth_test4'] == 'cli'
