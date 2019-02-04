import pkg_resources
import pkgutil

from lexicon import providers


def find_providers():
    providers_list = sorted({modname for (_, modname, _)
                             in pkgutil.iter_modules(providers.__path__)
                             if modname != 'base'})

    try:
        distribution = pkg_resources.get_distribution('dns-lexicon')
    except pkg_resources.DistributionNotFound:
        return {provider: True for provider in providers_list}
    else:
        return {provider: resolve_requirements(provider, distribution)
                for provider in providers_list}


def resolve_requirements(provider, distribution):
    try:
        requirements = distribution.requires([provider])
    except pkg_resources.UnknownExtra:
        # No extra for this provider
        return True
    else:
        # Extra is defined
        try:
            for requirement in requirements:
                pkg_resources.get_distribution(requirement)
        except (pkg_resources.DistributionNotFound, pkg_resources.VersionConflict):
            # At least one extra requirement is not fulfilled
            return False

    return True


def lexicon_version():
    try:
        return pkg_resources.get_distribution('dns-lexicon').version
    except pkg_resources.DistributionNotFound:
        return 'unknown'
