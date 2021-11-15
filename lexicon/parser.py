"""Parsers definition for the Lexicon command-line interface"""
import argparse
import importlib
import os
import sys
from typing import Tuple
from typing import Callable
import logging

from lexicon import discovery


def configure_base_provider_subparser(parser: argparse.ArgumentParser,
                                      provider_parser_config: Callable[[argparse.ArgumentParser], None]) -> None:
    """
    Function that configure the base provider subparser to be used by all dns providers.
    """
    subparsers = parser.add_subparsers(
        dest="action", help="specify the action to take",
    )
    subparsers.required = True

    for action in ["create", "list", "update", "delete"]:
        subparser = subparsers.add_parser(
            action,
            help=f"{action} action"
        )

        subparser.add_argument(
            "domain", help="specify the domain, supports subdomains as well", default=""
        )

        if action == "create":
            subparser.description = "Create a single DNS record."
            subparser.add_argument("record", help="the record to add, in BIND9 syntax")
        elif action == "update":
            subparser.description = "Update a single DNS record by identifier."
            subparser.add_argument("record", help="the updated record, in BIND9 syntax")
            group = subparser.add_argument_group(f"({action} action) required arguments")
            group.add_argument("--for-identifier", help="the identifier to filter for update",
                               required=True)
        elif action == "delete":
            subparser.description = "Delete one or more DNS records."
            group = subparser.add_argument_group(f"({action} action) optional arguments")
            group.add_argument("--for-identifier", help="the identifier to delete")
            group.add_argument("--for-type", help="the type to filter for delete",
                               default="TXT",
                               choices=["A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT", "SRV", "LOC"])
            group.add_argument("--for-name", help="the name to filter for delete")
            group.add_argument("--for-content", help="the content to filter for delete")
        else:  # Implicit list
            subparser.description = "List one or more DNS records."
            group = subparser.add_argument_group(f"({action} action) optional arguments")
            group.add_argument("--for-identifier", help="the identifier to filter for list")
            group.add_argument("--for-type", help="the type to filter for list",
                               default="TXT",
                               choices=["A", "AAAA", "CNAME", "MX", "NS", "SOA", "TXT", "SRV", "LOC"])
            group.add_argument("--for-name", help="the name to filter for list")
            group.add_argument("--for-content", help="the content to filter for list")

        provider_parser_config(subparser)


def configure_base_provider_legacy_subparser(parser: argparse.ArgumentParser) -> None:
    """
    Function that generates the base provider provider (legacy) to be used by all dns providers.
    """
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


def generate_cli_main_parser() -> Tuple[str, argparse.ArgumentParser]:
    parser_type = _guess_main_parser()

    if parser_type == "LEGACY":
        print("Warning: Legacy CLI detected. This CLI will be dropped "
              "in the next major version of Lexicon.", file=sys.stderr)

    parser = argparse.ArgumentParser(
        description="Create, update, delete or list DNS records in a DNS zone"
    )

    parser.add_argument(
        "--version",
        help="show the current version of lexicon",
        action="version",
        version=f"%(prog)s {discovery.lexicon_version()}",
    )
    parser.add_argument(
        "--legacy-cli",
        help="force usage of the legacy CLI",
        action="store_true",
    )

    def generic_parser_config(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--delegated", help="specify the delegated domain")
        subparser.add_argument(
            "--config-dir",
            default=os.getcwd(),
            help="specify the directory where to search lexicon.yml and "
                 "lexicon_[provider].yml configuration files "
                 "(default: current directory).",
        )
        subparser.add_argument(
            "--log_level",
            help="specify the log level",
            default="ERROR",
            choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"],
        )
        subparser.add_argument(
            "--output",
            help=(
                "specify the type of output: by default a formatted table (TABLE), "
                "a formatted table without header (TABLE-NO-HEADER), "
                "a JSON string (JSON) or no output (QUIET)"
            ),
            default="TABLE",
            choices=["TABLE", "TABLE-NO-HEADER", "JSON", "QUIET"],
        )

    subparsers = parser.add_subparsers(
        dest="provider_name", help="specify the DNS provider to use"
    )
    subparsers.required = True

    for provider, available in discovery.find_providers().items():
        provider_module = importlib.import_module("lexicon.providers." + provider)
        provider_parser = getattr(provider_module, "provider_parser")

        subparser = subparsers.add_parser(
            provider,
            help=f"{provider} provider",
        )
        if parser_type == "LEGACY":
            configure_base_provider_legacy_subparser(subparser)
            provider_parser(subparser)
        else:
            def parser_config(aparser: argparse.ArgumentParser) -> None:
                group = aparser.add_argument_group(f"({provider} provider) optional arguments")
                provider_parser(group)
                generic_parser_config(aparser)
            configure_base_provider_subparser(subparser, parser_config)

        if not available:
            subparser.epilog = (
                "WARNING: some required dependencies for this provider are not "
                f"installed. Please install lexicon[{provider}] first before using it."
            )

    return parser_type, parser


def _guess_main_parser() -> str:
    if "--legacy-cli" in sys.argv:
        return "LEGACY"

    if {"--name", "--content", "--identifier", "--ttl", "--priority"}.intersection(set(sys.argv)):
        return "LEGACY"

    if os.environ.get("LEXICON_LEGACY_CLI"):
        return "LEGACY"

    return "MODERN"
