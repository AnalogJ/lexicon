import os

from lexicon.config import ConfigurationResolver, ConfigFeeder
from lexicon.__main__ import MainParser

def test_environment_resolution():
    os.environ['LEXICON_DELEGATED'] = 'TEST1'
    os.environ['LEXICON_CLOUDFLARE_TOKEN'] = 'TEST2'
    os.environ['LEXICON_CLOUDFLARE_AUTH_USERNAME'] = 'TEST3'

    config = ConfigurationResolver().withEnv()

    assert config.resolve('lexicon:delegated') == 'TEST1'
    assert config.resolve('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.resolve('lexicon:cloudflare:auth_username') == 'TEST3'
    assert config.resolve('lexicon:nonexistent') is None

def test_argparse_resolution():
    parser = MainParser()
    data = parser.parse_args(['--delegated', 'TEST1', 'cloudflare', 'create', 'example.com', 'TXT', '--auth-token', 'TEST2'])

    config = ConfigurationResolver().withArgs(data)

    assert config.resolve('lexicon:delegated') == 'TEST1'
    assert config.resolve('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.resolve('lexicon:nonexistent') is None

def test_dict_resolution():
    dict_object = {
        'delegated': 'TEST1',
        'cloudflare': {
            'auth_token': 'TEST2'
        }
    }

    config = ConfigurationResolver().withDict(dict_object)

    assert config.resolve('lexicon:delegated') == 'TEST1'
    assert config.resolve('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.resolve('lexicon:nonexistent') is None

def test_config_lexicon_file_resolution(tmpdir):
    lexicon_file = tmpdir.join('lexicon.yml')
    lexicon_file.write('delegated: TEST1\ncloudflare:\n  auth_token: TEST2')

    config = ConfigurationResolver().withConfigFile(str(lexicon_file))

    assert config.resolve('lexicon:delegated') == 'TEST1'
    assert config.resolve('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.resolve('lexicon:nonexistent') is None

def test_provider_config_lexicon_file_resolution(tmpdir):
    provider_file = tmpdir.join('lexicon_cloudflare.yml')
    provider_file.write('auth_token: TEST2')

    config = ConfigurationResolver().withProviderConfigFile('cloudflare', str(provider_file))

    assert config.resolve('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.resolve('lexicon:nonexistent') is None

def test_provider_config_dir_resolution(tmpdir):
    lexicon_file = tmpdir.join('lexicon.yml')
    provider_file = tmpdir.join('lexicon_cloudflare.yml')
    lexicon_file.write('delegated: TEST1\ncloudflare:\n  auth_token: TEST2')
    provider_file.write('auth_username: TEST3')

    config = ConfigurationResolver().withConfigDir(str(tmpdir))

    assert config.resolve('lexicon:delegated') == 'TEST1'
    assert config.resolve('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.resolve('lexicon:cloudflare:auth_username') == 'TEST3'
    assert config.resolve('lexicon:nonexistent') is None

def test_generic_config_feeder_resolution():
    class GenericConfigFeeder(ConfigFeeder):
        
        def feed(self, config_key):
            return 'TEST1'

    config = ConfigurationResolver().withConfigFeeder(GenericConfigFeeder())

    assert config.resolve('lexicon:cloudflare:auth_username') == 'TEST1'
    assert config.resolve('lexicon:nonexistent') == 'TEST1'

def test_legacy_dict_config_resolution():
    legacy_config = {
        'delegated': 'TEST1',
        'auth_token': 'TEST2',
        'provider_name': 'cloudflare'
    }

    config = ConfigurationResolver().withLegacyDict(legacy_config)

    assert config.resolve('lexicon:delegated') == 'TEST1'
    assert config.resolve('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.resolve('lexicon:auth_token') is None
    assert config.resolve('lexicon:nonexistent') is None

def test_prioritized_resolution(tmpdir):
    lexicon_file = tmpdir.join('lexicon.yml')
    lexicon_file.write('cloudflare:\n  auth_token: TEST1')

    os.environ['LEXICON_CLOUDFLARE_AUTH_TOKEN'] = 'TEST2'

    assert ConfigurationResolver().withConfigFile(lexicon_file).withEnv().resolve('lexicon:cloudflare:auth_token') == 'TEST1'
    assert ConfigurationResolver().withEnv().withConfigFile(lexicon_file).resolve('lexicon:cloudflare:auth_token') == 'TEST2'
