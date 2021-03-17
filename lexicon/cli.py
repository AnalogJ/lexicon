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


def generate_list_table_result(lexicon_logger, output=None, without_header=None):
    """Convert returned data from list actions into a nice table for command line usage"""
    if not isinstance(output, list):
        lexicon_logger.debug('Command output is not a list, and then cannot '
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
    return os.linesep.join(table)


def generate_table_results(output=None, without_header=None):
    """Convert returned data from non-list actions into a nice table for command line usage"""
    array = []
    str_output = str(output)

    if not without_header:
        array.append('RESULT')
        array.append('-' * max(6, len(str_output)))

    array.append(str_output)
    return os.linesep.join(array)


def handle_output(results, output_type, action):
    """Print the relevant output for given output_type"""
    if output_type == 'QUIET':
        return

    if not output_type == 'JSON':
        if action == 'list':
            table = generate_list_table_result(
                logger, results, output_type == 'TABLE-NO-HEADER')
        else:
            table = generate_table_results(results, output_type == 'TABLE-NO-HEADER')
        if table:
            print(table)
    else:
        try:
            json_str = json.dumps(results)
            if json_str:
                print(json_str)
        except TypeError:
            logger.debug('Output is not JSON serializable, and then cannot '
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
    #   * from lexicon configuration files found in given --config-dir (default is current dir)
    config = ConfigResolver()
    config.with_args(parsed_args).with_env().with_config_dir(parsed_args.config_dir)

    client = Client(config)

    results = client.execute()

    handle_output(results, parsed_args.output, config.resolve('lexicon:action'))


if __name__ == '__main__':
    main()
