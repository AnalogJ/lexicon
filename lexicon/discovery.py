"""
This module takes care of finding information about the runtime of Lexicon:
* what are the providers installed, and available
* what is the version of Lexicon
"""
import pkgutil
from typing import Dict, List

import pkg_resources

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
        distribution = pkg_resources.get_distribution("dns-lexicon")
    except pkg_resources.DistributionNotFound:
        return {provider: True for provider in providers_list}
    else:
        return {
            provider: _resolve_requirements(provider, distribution)
            for provider in providers_list
        }


def lexicon_version() -> str:
    """Retrieve current Lexicon version"""
    try:
        return pkg_resources.get_distribution("dns-lexicon").version
    except pkg_resources.DistributionNotFound:
        return "unknown"


def _resolve_requirements(
    provider: str, distribution: pkg_resources.Distribution
) -> bool:
    try:
        requirements: List[pkg_resources.Requirement] = distribution.requires(
            extras=(provider,)
        )
    except pkg_resources.UnknownExtra:
        # No extra for this provider
        return True
    else:
        # Extra is defined
        try:
            for requirement in requirements:
                if hasattr(requirement, "name"):
                    pkg_resources.get_distribution(requirement.name)  # type: ignore
                else:
                    pkg_resources.get_distribution(requirement)
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
            # At least one extra requirement is not fulfilled
            return False

    return True
