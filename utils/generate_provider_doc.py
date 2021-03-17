#!/usr/bin/env python3
import argparse
import importlib
import os

from lexicon import discovery


def main():
    providers = [
        provider for provider in discovery.find_providers().keys() if provider != "auto"
    ]

    output = f"""\
Providers available
-------------------

The following Lexicon providers are available:

{_generate_table(["{0}_".format(provider) for provider in providers])}

List of options
---------------

"""

    for provider in providers:
        provider_module = importlib.import_module("lexicon.providers." + provider)
        parser = argparse.ArgumentParser()
        provider_module.provider_parser(parser)

        provider_content = [
            f"""\
.. _{provider}:

{provider}
"""
        ]
        for action in parser._actions:
            if action.dest == "help":
                continue

            provider_content.append(
                f"""\
    * ``{action.dest}`` {action.help.capitalize().replace("`", "'")}
"""
            )
        output = output + "".join(provider_content) + "\n"

    with open(os.path.join("docs", "providers_options.rst"), "w") as f:
        f.write(output)


def _generate_table(items):
    nb_columns = 4
    max_width = max(len(item) for item in items) + 1
    delimiter = f"+{'-' * (max_width + 1)}" * nb_columns + "+"

    table = [delimiter]

    divided = [items[n : n + nb_columns] for n in range(0, len(items), nb_columns)]
    divided[-1] = [
        divided[-1][i] if len(divided[-1]) > i else "" for i in range(0, nb_columns)
    ]

    for data in divided:
        line = "".join(f"| {item:<{max_width}}" for item in data) + "|"
        table = [*table, line, delimiter]

    return "\n".join(table)


if __name__ == "__main__":
    main()
