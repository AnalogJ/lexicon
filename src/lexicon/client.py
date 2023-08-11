"""Main module of Lexicon. Defines the Client class, that holds all Lexicon logic."""
import importlib
import logging
import os
from typing import Dict, List, Optional, Type, Union, cast

import tldextract  # type: ignore

from lexicon import config as helper_config
from lexicon import discovery
from lexicon.exceptions import ProviderNotAvailableError
from lexicon.providers.base import Provider


class _ClientExecutor:
    """
    Represents one set of commands against the Client
    for a given resolved Provider already authenticated.
    """

    def __init__(self, provider: Provider):
        self.provider = provider

    def create_record(self, rtype: str, name: str, content: str) -> bool:
        """
        Create record. If record already exists with the same content, do nothing.
        """
        return self.provider.create_record(rtype, name, content)

    def list_records(
        self,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> List[Dict]:
        """
        List all records. Return an empty list if no records found
        type, name and content are used to filter records.
        If possible filter during the query, otherwise filter after response is received.
        """
        return self.provider.list_records(rtype, name, content)

    def update_record(
        self,
        identifier: Optional[str] = None,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        """
        Update a record. Identifier must be specified.
        """
        return self.provider.update_record(identifier, rtype, name, content)

    def delete_record(
        self,
        identifier: Optional[str] = None,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        """
        Delete an existing record.
        If record does not exist, do nothing.
        If an identifier is specified, use it, otherwise do a lookup using type, name and content.
        """
        return self.provider.delete_record(identifier, rtype, name, content)


class Client:
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
        domain_parts = domain_extractor(
            cast(str, self.config.resolve("lexicon:domain"))
        )
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
        self.provider_class: Type[Provider] = getattr(provider_module, "Provider")
        self._provider: Provider

    def __enter__(self) -> "_ClientExecutor":
        self._provider = self.provider_class(self.config)
        self._provider.authenticate()
        return _ClientExecutor(self._provider)

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self._provider.cleanup()
        self._provider = None

    def execute(self) -> Union[bool, List[Dict]]:
        """Execute provided configuration in class constructor to the DNS records"""
        if not self.config.resolve("lexicon:action"):
            raise AttributeError("action")
        if not self.config.resolve("lexicon:type"):
            raise AttributeError("type")

        identifier = self.config.resolve("lexicon:identifier")
        record_type = self.config.resolve("lexicon:type")
        name = self.config.resolve("lexicon:name")
        content = self.config.resolve("lexicon:content")

        try:
            executor = self.__enter__()

            if self.action == "create":
                if not name or not content:
                    raise ValueError("Missing record_type, name or content parameters.")
                return executor.create_record(record_type, name, content)

            if self.action == "list":
                return executor.list_records(record_type, name, content)

            if self.action == "update":
                return executor.update_record(identifier, record_type, name, content)

            if self.action == "delete":
                return executor.delete_record(identifier, record_type, name, content)

            raise ValueError(f"Invalid action statement: {self.action}")
        finally:
            self.__exit__(None, None, None)

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
                    f"This provider ({provider_name}) has required extra dependencies that are missing. "
                    f"Please run `pip install dns-lexicon[{provider_name}]` first before using it."
                )

        if not self.config.resolve("lexicon:domain"):
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
