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
from lexicon.records import Record, RecordsFilter, from_dict


class ClientAction:
    def __init__(
        self, config: helper_config.ConfigResolver, provider: Provider
    ) -> None:
        self.config = config
        self.provider = provider

    def create(self, record: Record) -> bool:
        return self.provider.create_record(record.type, record.name, record.content)

    def list(self, record_filter: Optional[RecordsFilter] = None) -> List[Record]:
        if not record_filter:
            record_filter = RecordsFilter(
                identifier=None, type=None, name=None, content=None
            )
        output = self.provider.list_records(
            record_filter.type, record_filter.name, record_filter.content
        )

        return [from_dict(entry) for entry in output]

    def update(self, identifier: str, record: Record) -> bool:
        # In this new implementation, update() can only update record based on the identifier
        return self.provider.update_record(
            identifier, record.type, record.name, record.content
        )

    def delete(self, record_filter: RecordsFilter) -> bool:
        return self.provider.delete_record(
            record_filter.identifier,
            record_filter.type,
            record_filter.name,
            record_filter.content,
        )


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
        _validate_config(self.config)

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
        action = self.config.resolve("lexicon:action")
        record_type = self.config.resolve("lexicon:type")

        if not action:
            raise AttributeError("action")
        if not record_type:
            raise AttributeError("type")

        identifier = self.config.resolve("lexicon:identifier")
        name = self.config.resolve("lexicon:name")
        content = self.config.resolve("lexicon:content")

        self.provider.authenticate()

        if action == "create":
            if not record_type or not name or not content:
                raise ValueError("Missing record_type, name or content parameters.")
            return self.provider.create_record(record_type, name, content)

        if action == "list":
            return self.provider.list_records(record_type, name, content)

        if action == "update":
            return self.provider.update_record(identifier, record_type, name, content)

        if action == "delete":
            return self.provider.delete_record(identifier, record_type, name, content)

        raise ValueError(f"Invalid action statement: {action}")

    def __enter__(self) -> ClientAction:
        self.provider.authenticate()
        self.authenticated = True

        return ClientAction(self.config, self.provider)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def _validate_config(config: helper_config.ConfigResolver) -> None:
    provider_name = config.resolve("lexicon:provider_name")
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

    if not config.resolve("lexicon:domain"):
        raise AttributeError("domain")


def _get_tldextract_cache_path() -> str:
    if os.environ.get("TLDEXTRACT_CACHE_FILE"):
        logging.warning(
            "TLD_EXTRACT_CACHE_FILE environment variable is deprecated, please use TLDEXTRACT_CACHE_PATH instead."
        )
        os.environ["TLDEXTRACT_CACHE_PATH"] = os.environ["TLDEXTRACT_CACHE_FILE"]

    return os.path.expanduser(
        os.environ.get("TLDEXTRACT_CACHE_PATH", os.path.join("~", ".lexicon_tld_set"))
    )
