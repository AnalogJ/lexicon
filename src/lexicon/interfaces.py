"""Base provider module for all Lexicon providers"""
from __future__ import annotations

from abc import ABC, abstractmethod
from argparse import ArgumentParser
from re import Pattern
from typing import Any

from lexicon.config import ConfigResolver, legacy_config_resolver


class Provider(ABC):
    """
    This is the abstract class for all lexicon Providers.
    It provides common functionality and ensures that all implemented
    Providers follow a standard ducktype.
    All standardized options will be provided here as defaults, but can be overwritten
    by environmental variables and cli arguments.

    Common options are:

    action
    domain
    type
    name
    content
    ttl
    priority
    identifier

    The provider_env_cli_options will also contain any Provider specific options:

    auth_username
    auth_token
    auth_password
    ...

    :param config: is a ConfigResolver object that contains all the options
    for this provider, merged from CLI and Env variables.
    """

    def __init__(self, config: ConfigResolver | dict[str, Any]):
        if not isinstance(config, ConfigResolver):
            # If config is a plain dict, we are in a legacy situation.
            # To protect the Provider API, the legacy dict is handled in a
            # correctly defined ConfigResolver.
            # Also, there may be some situation where `provider` key is not set in the config.
            # It should not happen when Lexicon is called from Client, as it will set itself
            # this key. However, there were no automated logic if the Provider is used directly.
            # So we provide this logic here.
            if not config.get("provider_name") and not config.get("provider"):
                config[
                    "provider_name"
                ] = __name__  # Obviously we use the module name itself.
            self.config = legacy_config_resolver(config)
        else:
            self.config = config

        # Default ttl
        self.config.with_dict({"ttl": 3600})

        self.provider_name = self.config.resolve(
            "lexicon:provider_name"
        ) or self.config.resolve("lexicon:provider")
        self.domain = str(self.config.resolve("lexicon:domain"))
        self.domain_id = None

    # Provider API: instance methods

    @abstractmethod
    def authenticate(self) -> None:
        """
        Authenticate against provider,
        Make any requests required to get the domain's id for this provider,
        so it can be used in subsequent calls.
        Should throw AuthenticationError or requests.HTTPError if authentication fails for any reason,
        of if the domain does not exist.
        """

    def cleanup(self) -> None:
        """
        Clean any relevant resource before this provider instance is closed.
        """

    @abstractmethod
    def create_record(self, rtype: str, name: str, content: str) -> bool:
        """
        Create record. If record already exists with the same content, do nothing.
        """

    @abstractmethod
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

    @abstractmethod
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

    @abstractmethod
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

    # Provider API: static methods

    @staticmethod
    @abstractmethod
    def get_nameservers() -> list[str] | list[Pattern]:
        """
        Return the list of nameservers for this DNS provider
        """

    @staticmethod
    @abstractmethod
    def configure_parser(parser: ArgumentParser) -> None:
        """
        Configure the given parser for the provider needs
        (e.g. specific CLI flags for auth)
        """

    # Helpers

    def _request(
        self,
        action: str = "GET",
        url: str = "/",
        data: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an HTTP request against the DNS provider API"""
        raise NotImplementedError(
            "You must implement _request() to use _get()/_post()/_put()/_patch()/_delete() methods."
        )

    def _get(self, url: str = "/", query_params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", url, query_params=query_params)

    def _post(
        self,
        url: str = "/",
        data: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> Any:
        return self._request("POST", url, data=data, query_params=query_params)

    def _put(
        self,
        url: str = "/",
        data: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> Any:
        return self._request("PUT", url, data=data, query_params=query_params)

    def _patch(
        self,
        url: str = "/",
        data: dict[str, Any] | None = None,
        query_params: dict[str, Any] | None = None,
    ) -> Any:
        return self._request("PATCH", url, data=data, query_params=query_params)

    def _delete(
        self, url: str = "/", query_params: dict[str, Any] | None = None
    ) -> Any:
        return self._request("DELETE", url, query_params=query_params)

    def _fqdn_name(self, record_name: str) -> str:
        # strip trailing period from fqdn if present
        record_name = record_name.rstrip(".")
        # check if the record_name is fully specified
        if not record_name.endswith(self.domain):
            record_name = f"{record_name}.{self.domain}"
        return f"{record_name}."  # return the fqdn name

    def _full_name(self, record_name: str) -> str:
        # strip trailing period from fqdn if present
        record_name = record_name.rstrip(".")
        # check if the record_name is fully specified
        if not record_name.endswith(self.domain):
            record_name = f"{record_name}.{self.domain}"
        return record_name

    def _relative_name(self, record_name: str) -> str:
        # strip trailing period from fqdn if present
        record_name = record_name.rstrip(".")
        # check if the record_name is fully specified
        if record_name.endswith(self.domain):
            record_name = record_name[: -len(self.domain)]
            record_name = record_name.rstrip(".")
        return record_name

    def _clean_TXT_record(self, record: dict[str, Any]) -> dict[str, Any]:
        if record["type"] == "TXT":
            # Some providers have quotes around the TXT records,
            # so we're going to remove those extra quotes
            record["content"] = record["content"][1:-1]
        return record

    def _get_lexicon_option(self, option: str) -> str | None:
        return self.config.resolve(f"lexicon:{option}")

    def _get_provider_option(self, option: str) -> str | None:
        return self.config.resolve(f"lexicon:{self.provider_name}:{option}")
