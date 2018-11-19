#!/usr/bin/env python
"""Module for Lexicon command-line interface"""
from __future__ import absolute_import, print_function
import json
import logging
import os
import sys

from lexicon.client import Client
from lexicon.config import ConfigResolver
from lexicon.parser import generate_cli_main_parser


logger = logging.getLogger(__name__)  # pylint: disable=C0103


def generate_table_result(lexicon_logger, output=None, without_header=None):
    """Convert returned JSON into a nice table for command line usage"""
    try:
        _ = (entry for entry in output)
    except TypeError:
        lexicon_logger.debug('Command output is not iterable, and then cannot '
                             'be printed with --quiet parameter not enabled.')
        return None

    array = [[
        row.get('id', ''),
        row.get('type', ''),
        row.get('name', ''),
        row.get('content', ''),
        row.get('ttl', '')] for row in output]

    # Insert header (insert before calculating the max width of each column
    # to take headers size into account)
    if not without_header:
        headers = ['ID', 'TYPE', 'NAME', 'CONTENT', 'TTL']
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
        array.insert(1, ['-' * column_widths[idx]
                         for idx in range(len(column_widths))])

    # Construct table to be printed
    table = []
    for row in array:
        row_list = []
        for idx, col in enumerate(row):
            row_list.append(str(col).ljust(column_widths[idx]))
        table.append(' '.join(row_list))

    # Return table
    return '\n'.join(table)


def handle_output(results, output_type):
    """Print the relevant output for given output_type"""
    if not output_type == 'QUIET':
        if not output_type == 'JSON':
            table = generate_table_result(
                logger, results, output_type == 'TABLE-NO-HEADER')
            if table:
                print(table)
        else:
            try:
                _ = (entry for entry in results)
                json_str = json.dumps(results)
                if json_str:
                    print(json_str)
            except TypeError:
                logger.debug('Output is not a JSON, and then cannot '
                             'be printed with --output=JSON parameter.')


def main():
    """Main function of Lexicon."""
    # Dynamically determine all the providers available and gather command line arguments.
    parsed_args = generate_cli_main_parser().parse_args()

    log_level = logging.getLevelName(parsed_args.log_level)
    logging.basicConfig(stream=sys.stdout, level=log_level,
                        format='%(message)s')
    logger.debug('Arguments: %s', parsed_args)

    # In the CLI context, will get configuration interactively:
    #   * from the command line
    #   * from the environment variables
    #   * from lexicon configuration files in working directory
    config = ConfigResolver()
    config.with_args(parsed_args).with_env().with_config_dir(os.getcwd())

    client = Client(config)

    results = client.execute()

    handle_output(results, parsed_args.output)


if __name__ == '__main__':
    main()
