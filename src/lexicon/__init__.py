import sys
import warnings
from types import ModuleType

from lexicon._private import cli as _cli
from lexicon._private import discovery as _discovery
from lexicon._private import parser as _parser


class DeprecatedModule(ModuleType):
    def __init__(self, module: ModuleType, name: str):
        super().__init__(name)
        self._module = module

    def __getattr__(self, item):
        warnings.warn(
            f"Module {self.__name__} is deprecated and will be removed in Lexicon 4>=",
            DeprecationWarning,
            stacklevel=2,
        )
        return getattr(self._module, item)


sys.modules["lexicon.cli"] = DeprecatedModule(_cli, "lexicon.cli")
sys.modules["lexicon.parser"] = DeprecatedModule(_parser, "lexicon.parser")
sys.modules["lexicon.discovery"] = DeprecatedModule(_discovery, "lexicon.discovery")
