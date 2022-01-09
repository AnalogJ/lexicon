"""Unit tests for the Lexicon CLI parser"""
import pytest

from lexicon import parser


def test_cli_main_parser_with_cli_args():
    _, baseparser = parser.generate_cli_main_parser(parser_type="MODERN")
    parsed = baseparser.parse_args(["cloudflare", "list", "capsulecd.com", "--for-type", "TXT"])
    assert parsed.provider_name == "cloudflare"
    assert parsed.action == "list"
    assert parsed.domain == "capsulecd.com"
    assert parsed.for_type == "TXT"
    assert parsed.output == "TABLE"


def test_legacy_cli_main_parser_with_cli_args():
    _, baseparser = parser.generate_cli_main_parser(parser_type="LEGACY")
    parsed = baseparser.parse_args(["cloudflare", "list", "capsulecd.com", "TXT"])
    assert parsed.provider_name == "cloudflare"
    assert parsed.action == "list"
    assert parsed.domain == "capsulecd.com"
    assert parsed.type == "TXT"
    assert parsed.output == "TABLE"


def test_cli_main_parser_without_args():
    _, baseparser = parser.generate_cli_main_parser(parser_type="MODERN")
    with pytest.raises(SystemExit):
        baseparser.parse_args([])

def test_legacy_cli_main_parser_without_args():
    _, baseparser = parser.generate_cli_main_parser(parser_type="LEGACY")
    with pytest.raises(SystemExit):
        baseparser.parse_args([])
