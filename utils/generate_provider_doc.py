#!/usr/bin/env python3
import argparse
import os
import re
import shutil
from os.path import dirname, join
from typing import List, Type

from lexicon._private import discovery
from lexicon._private.discovery import load_provider_module
from lexicon._private.providers.valuedomain import Provider

_ROOT = dirname(dirname(__file__))
_DOCS = os.path.join(_ROOT, "docs")
_PROVIDERS = os.path.join(_DOCS, "providers")


def main() -> None:
    providers = [
        provider for provider in discovery.find_providers().keys() if provider != "auto"
    ]

    shutil.rmtree(_PROVIDERS, ignore_errors=True)
    os.mkdir(_PROVIDERS)

    _generate_table(providers)

    output = [
        """
Providers available
-------------------

The following Lexicon providers are available:

.. include:: ../README.rst
    :start-after: tag: providers-table-begin
    :end-before: tag: providers-table-end

List of options
---------------
"""
    ]

    for provider in providers:
        _generate_provider_details(provider)
        output.append(
            f"""\
.. _{provider}:
.. include:: providers/{provider}.rst
"""
        )

    with open(join(_DOCS, "providers_options.rst"), "w") as f:
        f.write("\n".join(output))


def _generate_table(providers: List[str]) -> None:
    items = [f"{provider}_" for provider in providers]
    nb_columns = 5
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

    with open(join(_ROOT, "README.rst")) as f:
        readme_lines = f.readlines()

    begin_idx = readme_lines.index(".. tag: providers-table-begin\n")
    end_idx = readme_lines.index(".. tag: providers-table-end\n")

    readme_lines = (
        readme_lines[: begin_idx + 1]
        + ["\n"]
        + [f"{item}\n" for item in table]
        + ["\n"]
        + readme_lines[end_idx:]
    )

    with open(join(_ROOT, "README.rst"), "w") as f:
        f.writelines(readme_lines)


def _generate_provider_details(provider: str) -> None:
    provider_module = load_provider_module(provider)
    provider_class: Type[Provider] = getattr(provider_module, "Provider")
    parser = argparse.ArgumentParser()
    provider_class.configure_parser(parser)

    output = [provider]

    for action in parser._actions:
        if action.dest == "help":
            continue

        output.append(
            f"""\
    * ``{action.dest}`` {action.help.capitalize().replace("`", "'")}
"""
        )

    if parser.description:
        output.append(
            f"""
.. note::
   
{_cleanup_description(parser.description)}

"""
        )

    with open(join(_PROVIDERS, f"{provider}.rst"), "w") as f:
        f.write("\n".join(output))


def _cleanup_description(description: str):
    lines = description.split(os.linesep)
    if not lines:
        return ""
    if not lines[0]:
        lines.pop(0)
    if not lines:
        return ""
    match = re.match(r"^(\s*)\S.*$", lines[0])
    first_ident = len(match.group(1)) if match else 0
    lines = [f"   {line[first_ident:]}" for line in lines]
    return os.linesep.join(lines)


if __name__ == "__main__":
    main()
