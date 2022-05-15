"""
This module takes care of finding information about the runtime of Lexicon:
* what are the providers installed, and available
* what is the version of Lexicon
"""
import pkgutil
import re
from typing import Dict

try:
    from importlib.metadata import Distribution, PackageNotFoundError
except ModuleNotFoundError:
    from importlib_metadata import Distribution, PackageNotFoundError  # type: ignore[misc]

from lexicon import providers


def find_providers() -> Dict[str, bool]:
    """Find all providers registered in Lexicon, and their availability"""
    providers_list = sorted(
        {
            modname
            for (_, modname, _) in pkgutil.iter_modules(providers.__path__)  # type: ignore
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

    requirements = [
        re.sub(r"^(.*)\s\(.*\)(?:;.*|)$", r"\1", requirement)
        for requirement in requires
        if f'extra == "{provider}"' in requirement
    ]

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
