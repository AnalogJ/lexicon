"""Parsers definition for the Lexicon command-line interface"""

import argparse
import os
from typing import Type

from lexicon._private.discovery import (
    find_providers,
    lexicon_version,
    load_provider_module,
)
from lexicon.interfaces import Provider


def generate_base_provider_parser() -> argparse.ArgumentParser:
    """Function that generates the base provider to be used by all dns providers."""
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "action",
        help="specify the action to take",
        default="list",
        choices=["create", "list", "update", "delete"],
    )
    parser.add_argument(
        "domain", help="specify the domain, supports subdomains as well"
    )
    parser.add_argument(
        "type",
        help="specify the entry type",
        default="TXT",
        choices=["A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT", "SRV", "LOC"],
    )

    parser.add_argument("--name", help="specify the record name")
    parser.add_argument("--content", help="specify the record content")
    parser.add_argument("--ttl", type=int, help="specify the record time-to-live")
    parser.add_argument("--priority", help="specify the record priority")
    parser.add_argument(
        "--identifier", help="specify the record for update or delete actions"
    )
    parser.add_argument(
        "--log-level",
        "--log_level",
        help="specify the log level",
        default="ERROR",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
    )
    parser.add_argument(
        "--output",
        help=(
            "specify the type of output: by default a formatted table (TABLE), "
            "a formatted table without header (TABLE-NO-HEADER), "
            "a JSON string (JSON) or no output (QUIET)"
        ),
        default="TABLE",
        choices=["TABLE", "TABLE-NO-HEADER", "JSON", "QUIET"],
    )
    return parser


def generate_cli_main_parser() -> argparse.ArgumentParser:
    """Using all providers available, generate a parser that will be used by Lexicon CLI"""
    parser = argparse.ArgumentParser(
        description="Create, Update, Delete, List DNS entries"
    )

    parser.add_argument(
        "--version",
        help="show the current version of lexicon",
        action="version",
        version=f"%(prog)s {lexicon_version()}",
    )
    parser.add_argument(
        "--delegated",
        help="specify the delegated domain (may not needed if --resolve-zone-name is set)",
    )
    parser.add_argument(
        "--config-dir",
        default=os.getcwd(),
        help="specify the directory where to search lexicon.yml and "
        "lexicon_[provider].yml configuration files "
        "(default: current directory).",
    )
    parser.add_argument(
        "--resolve-zone-name",
        action="store_true",
        help="trigger an active resolution of the zone name for the given domain using DNS queries",
    )
    subparsers = parser.add_subparsers(
        dest="provider_name", help="specify the DNS provider to use"
    )
    subparsers.required = True

    for provider, available in find_providers().items():
        provider_module = load_provider_module(provider)
        provider_class: Type[Provider] = getattr(provider_module, "Provider")

        subparser = subparsers.add_parser(
            provider,
            help=f"{provider} provider",
            parents=[generate_base_provider_parser()],
        )

        provider_class.configure_parser(subparser)

        if not available:
            subparser.epilog = (
                "WARNING: some required dependencies for this provider are not "
                f"installed. Please run `pip install lexicon[{provider}]` first before using it."
            )

    return parser
