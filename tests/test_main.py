import lexicon.__main__
import pytest

def test_BaseProviderParser():
    baseparser = lexicon.__main__.BaseProviderParser()
    parsed = baseparser.parse_args(['list','capsulecd.com','TXT'])
    assert parsed.action == 'list'
    assert parsed.domain == 'capsulecd.com'
    assert parsed.type == 'TXT'
    assert parsed.ttl == None


def test_BaseProviderParser_without_domain():
    baseparser = lexicon.__main__.BaseProviderParser()
    with pytest.raises(SystemExit):
        baseparser.parse_args(['list'])

def test_BaseProviderParser_without_options():
    baseparser = lexicon.__main__.BaseProviderParser()
    with pytest.raises(SystemExit):
        baseparser.parse_args([])

def test_MainParser():
    baseparser = lexicon.__main__.MainParser()
    parsed = baseparser.parse_args(['cloudflare','list','capsulecd.com','TXT'])
    assert parsed.provider_name == 'cloudflare'
    assert parsed.action == 'list'
    assert parsed.domain == 'capsulecd.com'
    assert parsed.type == 'TXT'

def test_MainParser_without_args():
    baseparser = lexicon.__main__.MainParser()
    with pytest.raises(SystemExit):
        baseparser.parse_args([])

def test_MainParser_with_multi_contents():
    baseparser = lexicon.__main__.MainParser()
    parsed = baseparser.parse_args(['cloudflare','create','capsulecd.com','A','--content','127.0.0.1','--content','127.0.0.2'])
    assert type(parsed.content) is list
    assert len(parsed.content) == 2
    assert parsed.content[0] == '127.0.0.1'
    assert parsed.content[1] == '127.0.0.2'
