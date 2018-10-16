import os

from lexicon.config import ConfigurationResolver
from lexicon.__main__ import MainParser

def test_environment_resolution():
    os.environ['LEXICON_DELEGATED'] = 'TEST1'
    os.environ['LEXICON_CLOUDFLARE_TOKEN'] = 'TEST2'
    os.environ['LEXICON_CLOUDFLARE_AUTH_USERNAME'] = 'TEST3'

    config = ConfigurationResolver().withEnv()

    assert config.get('lexicon:delegated') == 'TEST1'
    assert config.get('lexicon:cloudflare:auth_token') == 'TEST2'
    assert config.get('lexicon:cloudflare:auth_username') == 'TEST3'

def test_argparse_resolution():
    parser = MainParser()
    data = parser.parse_args(['--delegated', 'TEST1', 'cloudflare', 'create', 'example.com', 'TXT', '--auth-token', 'TEST2'])

    config = ConfigurationResolver().withArgs(data)

    assert config.get('lexicon:delegated') == 'TEST1'
    assert config.get('lexicon:cloudflare:auth_token') == 'TEST2'

test_environment_resolution()