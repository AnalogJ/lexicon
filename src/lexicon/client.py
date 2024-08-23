"""Main module of Lexicon. Defines the Client class, that holds all Lexicon logic."""

from __future__ import annotations

import logging
import os
import warnings
from contextlib import AbstractContextManager
from threading import local
from types import TracebackType
from typing import Any, Type

import dns.resolver
import tldextract

from lexicon import config as helper_config
from lexicon._private.discovery import find_providers as _find_providers
from lexicon._private.discovery import load_provider_module as _load_provider_module
from lexicon.exceptions import ProviderNotAvailableError
from lexicon.interfaces import Provider


class _ClientOperations:
    """
    Represents the entrypoint to execute several operations against the Client
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
        rtype: str | None = None,
        name: str | None = None,
        content: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List all records. Return an empty list if no records found
        type, name and content are used to filter records.
        If possible filter during the query, otherwise filter after response is received.
        """
        return self.provider.list_records(rtype, name, content)

    def update_record(
        self,
        identifier: str | None = None,
        rtype: str | None = None,
        name: str | None = None,
        content: str | None = None,
    ) -> bool:
        """
        Update a record. Identifier must be specified.
        """
        return self.provider.update_record(identifier, rtype, name, content)

    def delete_record(
        self,
        identifier: str | None = None,
        rtype: str | None = None,
        name: str | None = None,
        content: str | None = None,
    ) -> bool:
        """
        Delete an existing record.
        If record does not exist, do nothing.
        If an identifier is specified, use it, otherwise do a lookup using type, name and content.
        """
        return self.provider.delete_record(identifier, rtype, name, content)


class Client(AbstractContextManager):
    """This is the Lexicon client, that will execute all the logic."""

    def __init__(
        self, config: helper_config.ConfigResolver | dict[str, Any] | None = None
    ):
        if not config:
            # If there is no config specified, we load a non-interactive configuration.
            self.config = helper_config.non_interactive_config_resolver()
        elif not isinstance(config, helper_config.ConfigResolver):
            # If config is not a ConfigResolver, we are in a legacy situation.
            # We protect this part of the Client API.
            self.config = helper_config.legacy_config_resolver(config)
        else:
            self.config = config

        domain = self.config.resolve("lexicon:domain")
        if not domain:
            raise AttributeError("domain")

        self._validate_provider()

        runtime_config = {}

        # Find the actual zone name for the domain
        if self.config.resolve("lexicon:resolve_zone_name") is not None:
            logging.debug(
                "Parameter resolve_zone_name is set, use dnspython to resolve the actual zone name"
            )
            zone_name = dns.resolver.zone_for_name(domain)
            runtime_config["domain"] = zone_name.to_text(omit_final_dot=True)
        else:
            logging.debug(
                "Parameter resolve_zone_name is not set, use tldextract to guess the zone name from known TLDs"
            )
            try:
                domain_extractor = tldextract.TLDExtract(
                    cache_dir=_resolve_tldextract_cache_path(),
                    include_psl_private_domains=True,
                )
            except TypeError:
                domain_extractor = tldextract.TLDExtract(
                    cache_file=_resolve_tldextract_cache_path(), include_psl_private_domains=True  # type: ignore
                )
            domain_parts = domain_extractor(domain)
            runtime_config["domain"] = f"{domain_parts.domain}.{domain_parts.suffix}"
        logging.debug(
            f"Actual zone name resolved for domain {domain}: {runtime_config['domain']}"
        )

        delegated = self.config.resolve("lexicon:delegated")
        if delegated:
            # handle delegated domain
            delegated = str(delegated).rstrip(".")
            initial_domain = str(runtime_config["domain"])
            if delegated != initial_domain:
                # convert to relative name
                if delegated.endswith(initial_domain):
                    delegated = delegated[: -len(initial_domain)]
                    delegated = delegated.rstrip(".")
                # update domain
                runtime_config["domain"] = f"{delegated}.{initial_domain}"
            logging.debug(
                f"Override resolved zone name because --delegated option is set: {runtime_config['domain']}"
            )

        self.provider_name = self.config.resolve(
            "lexicon:provider_name"
        ) or self.config.resolve("lexicon:provider")

        if not self.provider_name:
            raise ValueError("Could not resolve provider name.")

        self.config.add_config_source(helper_config.DictConfigSource(runtime_config), 0)

        provider_module = _load_provider_module(self.provider_name)
        self.provider_class: Type[Provider] = getattr(provider_module, "Provider")

        self._state = local()
        self._state.stack = []

    def __enter__(self) -> _ClientOperations:
        try:
            provider = self.provider_class(self.config)
            provider.authenticate()

            self._state.stack.append(provider)

            return _ClientOperations(provider)
        except Exception as e:
            self._state.stack.append(None)
            raise e

    def __exit__(
        self,
        __exc_type: type[BaseException] | None,
        __exc_value: BaseException | None,
        __traceback: TracebackType | None,
    ) -> bool | None:
        provider: Provider | None = self._state.stack.pop(-1)
        if provider:
            provider.cleanup()

        return None

    def execute(self) -> bool | list[dict[str, Any]]:
        """(deprecated) Execute provided configuration in class constructor to the DNS records"""
        message = """\
Method execute() is deprecated and will be removed in Lexicon 4>=.

Please remove action/type/name/content fields from Lexicon config,
and use the methods dedicated for each action (*_record()/list_records()).
These methods are available within the Lexicon client context manager.

Example for creating a record:

with Client(config) as operations:
    operations.create_record("TXT", "foo", "bar")
        """

        warnings.warn(message, DeprecationWarning, stacklevel=2)

        action = self.config.resolve("lexicon:action")
        identifier = self.config.resolve("lexicon:identifier")
        rtype = self.config.resolve("lexicon:type")
        name = self.config.resolve("lexicon:name")
        content = self.config.resolve("lexicon:content")

        if not action:
            raise AttributeError("action")
        if not rtype:
            raise AttributeError("type")

        try:
            executor = self.__enter__()

            if action == "create":
                if not name or not content:
                    raise ValueError("Missing record_type, name or content parameters.")
                return executor.create_record(rtype, name, content)

            if action == "list":
                return executor.list_records(rtype, name, content)

            if action == "update":
                return executor.update_record(identifier, rtype, name, content)

            if action == "delete":
                return executor.delete_record(identifier, rtype, name, content)

            raise ValueError(f"Invalid action statement: {action}")
        finally:
            self.__exit__(None, None, None)

    def _validate_provider(self) -> None:
        provider_name = self.config.resolve("lexicon:provider_name")
        if not provider_name:
            raise AttributeError("provider_name")

        try:
            available = _find_providers()[provider_name]
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


def _resolve_tldextract_cache_path() -> str:
    if os.environ.get("TLDEXTRACT_CACHE_FILE"):
        logging.warning(
            "TLD_EXTRACT_CACHE_FILE environment variable is deprecated, please use TLDEXTRACT_CACHE_PATH instead."
        )
        os.environ["TLDEXTRACT_CACHE_PATH"] = os.environ["TLDEXTRACT_CACHE_FILE"]

    return os.path.expanduser(
        os.environ.get("TLDEXTRACT_CACHE_PATH", os.path.join("~", ".lexicon_tld_set"))
    )
