import sys
import warnings

from lexicon._private.discovery import find_providers, load_provider_module

warnings.warn(
    """\
Package lexicon.providers is deprecated and will be removed in Lexicon 4>=.

Providers implementations are private, and are not meant to be used directly. Please use lexicon.client.Client instead.
Base provider interface is migrated to lexicon.interfaces.provider. Please use it instead to implement a new provider.
""",
    DeprecationWarning,
    stacklevel=2,
)

for module_name, available in find_providers().items():
    sys.modules[f"lexicon.providers.{module_name}"] = load_provider_module(module_name)
