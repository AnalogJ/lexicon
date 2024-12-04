"""
This module takes care of finding information about the runtime of Lexicon:
* what are the providers installed, and available
* what is the version of Lexicon
"""

from __future__ import annotations

import importlib
import pkgutil
import re
import sys
from types import ModuleType
from typing import Dict

from lexicon._private import providers as _providers

if sys.version_info >= (3, 10):  # pragma: no cover
    from importlib.metadata import Distribution, PackageNotFoundError
else:
    from importlib_metadata import Distribution, PackageNotFoundError


def find_providers() -> Dict[str, bool]:
    """Find all providers registered in Lexicon, and their availability"""
    providers_list = sorted(
        {
            modname
            for (_, modname, _) in pkgutil.iter_modules(_providers.__path__)
            if modname != "base"
        }
    )

    try:
        distribution = Distribution.from_name("dns-lexicon")
    except PackageNotFoundError:
        return {provider: True for provider in providers_list}
    else:
        return {
            provider: _resolve_requirements(provider, distribution)
            for provider in providers_list
        }


def load_provider_module(provider_name: str) -> ModuleType:
    return importlib.import_module(f"{_providers.__name__}.{provider_name}")


def lexicon_version() -> str:
    """Retrieve current Lexicon version"""
    try:
        return Distribution.from_name("dns-lexicon").version
    except PackageNotFoundError:
        return "unknown"


def _resolve_requirements(provider: str, distribution: Distribution) -> bool:
    requires = distribution.requires
    if requires is None:
        raise ValueError("Error while trying finding requirements.")

    requirements: list[str] = []
    for require in requires:
        match = re.match(
            rf"^([\w-]+)\s*[<>=]+\s*[\d\.-]+\s*;\s*extra\s*==\s*(?:\"|'){provider}(?:\"|')$",
            require,
        )

        if match is not None:
            requirements.append(match.group(1))

    if not requirements:
        # No extra for this provider
        return True

    for requirement in requirements:
        try:
            Distribution.from_name(requirement)
        except PackageNotFoundError:
            # At least one extra requirement is not fulfilled
            return False

    # All extra requirements are fulfilled
    return True
