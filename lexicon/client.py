"""Main module of Lexicon. Defines the Client class, that holds all Lexicon logic."""
import importlib
import logging
import os
from typing import Dict, List, Optional, Type, Union

import tldextract  # type: ignore

from lexicon import config as helper_config
from lexicon import discovery
from lexicon.exceptions import ProviderNotAvailableError
from lexicon.providers.base import Provider


class Client(object):
    """This is the Lexicon client, that will execute all the logic."""

    def __init__(
        self, config: Optional[Union[helper_config.ConfigResolver, Dict]] = None
    ):
        if not config:
            # If there is not config specified, we load a non-interactive configuration.
            self.config = helper_config.non_interactive_config_resolver()
        elif not isinstance(config, helper_config.ConfigResolver):
            # If config is not a ConfigResolver, we are in a legacy situation.
            # We protect this part of the Client API.
            self.config = helper_config.legacy_config_resolver(config)
        else:
            self.config = config

        # Validate configuration
        self._validate_config()

        runtime_config = {}

        # Process domain, strip subdomain
        try:
            domain_extractor = tldextract.TLDExtract(
                cache_dir=_get_tldextract_cache_path(), include_psl_private_domains=True
            )
        except TypeError:
            domain_extractor = tldextract.TLDExtract(
                cache_file=_get_tldextract_cache_path(), include_psl_private_domains=True  # type: ignore
            )
        domain_parts = domain_extractor(self.config.resolve("lexicon:domain"))
        runtime_config["domain"] = f"{domain_parts.domain}.{domain_parts.suffix}"

        delegated = self.config.resolve("lexicon:delegated")
        if delegated:
            # handle delegated domain
            delegated = str(delegated).rstrip(".")
            initial_domain = str(runtime_config.get("domain"))
            if delegated != initial_domain:
                # convert to relative name
                if delegated.endswith(initial_domain):
                    delegated = delegated[: -len(initial_domain)]
                    delegated = delegated.rstrip(".")
                # update domain
                runtime_config["domain"] = f"{delegated}.{initial_domain}"

        self.action = self.config.resolve("lexicon:action")
        self.provider_name = self.config.resolve(
            "lexicon:provider_name"
        ) or self.config.resolve("lexicon:provider")

        if not self.provider_name:
            raise ValueError("Could not resolve provider name.")

        self.config.add_config_source(helper_config.DictConfigSource(runtime_config), 0)

        provider_module = importlib.import_module(
            "lexicon.providers." + self.provider_name
        )
        provider_class: Type[Provider] = getattr(provider_module, "Provider")
        self.provider = provider_class(self.config)

    def execute(self) -> Union[bool, List[Dict]]:
        """Execute provided configuration in class constructor to the DNS records"""
        self.provider.authenticate()
        identifier = self.config.resolve("lexicon:identifier")
        record_type = self.config.resolve("lexicon:type")
        name = self.config.resolve("lexicon:name")
        content = self.config.resolve("lexicon:content")

        if self.action == "create":
            if not record_type or not name or not content:
                raise ValueError("Missing record_type, name or content parameters.")
            return self.provider.create_record(record_type, name, content)

        if self.action == "list":
            return self.provider.list_records(record_type, name, content)

        if self.action == "update":
            return self.provider.update_record(identifier, record_type, name, content)

        if self.action == "delete":
            return self.provider.delete_record(identifier, record_type, name, content)

        raise ValueError(f"Invalid action statement: {self.action}")

    def _validate_config(self) -> None:
        provider_name = self.config.resolve("lexicon:provider_name")
        if not provider_name:
            raise AttributeError("provider_name")

        try:
            available = discovery.find_providers()[provider_name]
        except KeyError:
            raise ProviderNotAvailableError(
                f"This provider ({provider_name}) is not supported by Lexicon."
            )
        else:
            if not available:
                raise ProviderNotAvailableError(
                    f"This provider ({provider_name}) has required dependencies that are missing. "
                    f"Please install lexicon[{provider_name}] first."
                )

        if not self.config.resolve("lexicon:action"):
            raise AttributeError("action")
        if not self.config.resolve("lexicon:domain"):
            raise AttributeError("domain")
        if not self.config.resolve("lexicon:type"):
            raise AttributeError("type")


def _get_tldextract_cache_path() -> str:
    if os.environ.get("TLDEXTRACT_CACHE_FILE"):
        logging.warning(
            "TLD_EXTRACT_CACHE_FILE environment variable is deprecated, please use TLDEXTRACT_CACHE_PATH instead."
        )
        os.environ["TLDEXTRACT_CACHE_PATH"] = os.environ["TLDEXTRACT_CACHE_FILE"]

    return os.path.expanduser(
        os.environ.get("TLDEXTRACT_CACHE_PATH", os.path.join("~", ".lexicon_tld_set"))
    )
