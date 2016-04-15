import lexicon.__main__
import pytest

def test_BaseProviderParser():
    baseparser = lexicon.__main__.BaseProviderParser()
    parsed = baseparser.parse_args(['list','capsulecd.com','TXT'])
    assert parsed.action == 'list'
    assert parsed.domain == 'capsulecd.com'
    assert parsed.type == 'TXT'


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
