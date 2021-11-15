#!/usr/bin/env python
"""Module for Lexicon command-line interface"""
import json
import logging
import os
import sys
from typing import Dict, List, Optional, Union, Any

from lexicon.client import Client
from lexicon.config import ConfigResolver
from lexicon.parser import generate_cli_main_parser
from lexicon.records import RecordsFilter, Record, from_text

logger = logging.getLogger(__name__)


def generate_list_table_result(
    lexicon_logger: logging.Logger,
    output: Optional[Union[bool, List[Record]]] = None,
    without_header: Optional[bool] = None,
) -> Optional[str]:
    """Convert returned data from list actions into a nice table for command line usage"""
    if not isinstance(output, List):
        lexicon_logger.debug(
            "Command output is not a list or records, and then cannot be printed as a table."
        )
        return None

    array = [
        [
            row.identifier or "",
            row.type or "",
            row.name or "",
            row.content or "",
            row.ttl or "",
        ]
        for row in output
    ]

    # Insert header (insert before calculating the max width of each column
    # to take headers size into account)
    if not without_header:
        headers = ["ID", "TYPE", "NAME", "CONTENT", "TTL"]
        array.insert(0, headers)

    column_widths = [0, 0, 0, 0, 0]
    # Find max width for each column
    for row in array:
        for idx, col in enumerate(row):
            width = len(str(col))
            if width > column_widths[idx]:
                column_widths[idx] = width

    # Add a 'nice' separator
    if not without_header:
        array.insert(1, ["-" * column_widths[idx] for idx in range(len(column_widths))])

    # Construct table to be printed
    table = []
    for row in array:
        row_list = []
        for idx, col in enumerate(row):
            row_list.append(str(col).ljust(column_widths[idx]))
        table.append(" ".join(row_list))

    # Return table
    return os.linesep.join(table)


def generate_table_results(
    output: Union[bool, List[Record]] = None, without_header: Optional[bool] = None
) -> str:
    """Convert returned data from non-list actions into a nice table for command line usage"""
    array = []
    str_output = str(output)

    if not without_header:
        array.append("RESULT")
        array.append("-" * max(6, len(str_output)))

    array.append(str_output)
    return os.linesep.join(array)


def handle_output(
    results: Union[bool, List[Record]], output_type: str, action: str
) -> None:
    """Print the relevant output for given output_type"""
    if output_type == "QUIET":
        return

    if output_type in ["TABLE", "TABLE-NO-HEADER"]:
        if action == "list":
            table = generate_list_table_result(
                logger, results, output_type == "TABLE-NO-HEADER"
            )
        else:
            table = generate_table_results(results, output_type == "TABLE-NO-HEADER")
        if table:
            print(table)
        return

    if output_type == "BIND9":
        if isinstance(results, List):
            for result in results:
                print(result.to_text())
        else:
            logger.debug(
                "Command output is not a list or records, and then cannot be printed as a table."
            )
        return

    # Default case: JSON
    try:
        json_str = json.dumps([result.to_dict() for result in results])
        if json_str:
            print(json_str)
    except TypeError:
        logger.debug(
            "Output is not JSON serializable, and then cannot "
            "be printed with --output=JSON parameter."
        )


def main() -> None:
    """Main function of Lexicon."""
    # Dynamically determine all the providers available and gather command line arguments.
    parser_type, parser = generate_cli_main_parser()
    parsed_args = parser.parse_args()

    log_level = logging.getLevelName(parsed_args.log_level)
    logging.basicConfig(stream=sys.stdout, level=log_level, format="%(message)s")
    logger.debug("Arguments: %s", parsed_args)

    # In the CLI context, will get configuration interactively:
    #   * from the command line
    #   * from the environment variables
    #   * from lexicon configuration files found in given --config-dir (default is current dir)
    config = ConfigResolver()
    config.with_args(parsed_args).with_env().with_config_dir(parsed_args.config_dir)

    action = config.resolve("lexicon:action")
    if not action:
        raise ValueError("Parameter action is not set.")

    results: Union[bool, List[Record]]
    if parser_type == "LEGACY":
        client = Client(config)

        results_raw = client.execute()
        if isinstance(results_raw, list):
            results = [Record.from_dict(dict_) for dict_ in results_raw]
        else:
            results = results_raw
    else:
        record_filter = RecordsFilter(
            identifier=config.resolve("lexicon:for_identifier"),
            type=config.resolve("lexicon:for_type"),
            name=config.resolve("lexicon:for_name"),
            content=config.resolve("lexicon:for_content"),
        )

        record = config.resolve("lexicon:record")

        with Client(config) as client_action:
            if action == "create":
                results = client_action.create(from_text(record))
            elif action == "update":
                results = client_action.update(record_filter.identifier, from_text(record))
            elif action == "delete":
                results = client_action.delete(record_filter)
            else:  # Implicit list
                results = client_action.list(record_filter)

    handle_output(results, parsed_args.output, action)


if __name__ == "__main__":
    main()
