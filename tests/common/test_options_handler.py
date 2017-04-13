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

def test_OptionsWithFallback_returns_none_when_no_fallbackFn_set():
    options = SafeOptionsWithFallback()
    assert options['test'] == None

def test_OptionsWithFallback_with_only_data_should_return():
    options = SafeOptionsWithFallback({'foo': 'bar'})
    assert options['test'] == None
    assert options['foo'] == 'bar'


def test_OptionsWithFallback_returns_none_when_no_fallbackFn_set():
    options = SafeOptionsWithFallback({}, lambda x: 'prepare_' + x)
    assert options['test'] == None