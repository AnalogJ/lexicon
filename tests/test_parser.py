"""Unit tests for the Lexicon CLI parser"""
import pytest

from lexicon import parser


def test_base_provider_parser():
    baseparser = parser.generate_base_provider_parser()
    parsed = baseparser.parse_args(["list", "capsulecd.com", "TXT"])
    assert parsed.action == "list"
    assert parsed.domain == "capsulecd.com"
    assert parsed.type == "TXT"
    assert parsed.ttl is None
    assert parsed.output == "TABLE"


def test_base_provider_parser_without_domain():
    baseparser = parser.generate_base_provider_parser()
    with pytest.raises(SystemExit):
        baseparser.parse_args(["list"])


def test_base_provider_parser_without_options():
    baseparser = parser.generate_base_provider_parser()
    with pytest.raises(SystemExit):
        baseparser.parse_args([])


def test_cli_main_parser():
    baseparser = parser.generate_cli_main_parser()
    parsed = baseparser.parse_args(["cloudflare", "list", "capsulecd.com", "TXT"])
    assert parsed.provider_name == "cloudflare"
    assert parsed.action == "list"
    assert parsed.domain == "capsulecd.com"
    assert parsed.type == "TXT"
    assert parsed.output == "TABLE"


def test_cli_main_parser_without_args():
    baseparser = parser.generate_cli_main_parser()
    with pytest.raises(SystemExit):
        baseparser.parse_args([])
