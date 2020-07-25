=======================
Configuration reference
=======================

Providers options
=================

.. include:: providers_options.rst

Passing provider options to Lexicon
===================================

There are three ways to pass a provider option to Lexicon (we suppose here that the
provider option is named ``auth_token``:

* by **CLI flag**: set the flag ``--auth-token`` to Lexicon while invoking it, for instance:

  .. code-block:: bash

        $ lexicon cloudflare create domain.net TXT --name foo --content bar --auth-token YOUR_TOKEN

* by **environment variable**: set the environment variable ``LEXICON_CLOUDFLARE_AUTH_TOKEN``, for instance:

  .. code-block:: bash

        $ LEXICON_CLOUDFLARE_AUTH_TOKEN=YOUR_TOKEN cloudflare create domain.net TXT --name foo --content bar

* by **configuration file**: construct a configuration file containing the provider options, for instance:

  .. code-block:: bash

        $ cat /path/to/config/lexicon.yml
        cloudflare:
          auth_token: YOUR_TOKEN
        $ lexicon cloudflare create domain.net TXT --name foo --content bar --config-dir /path/to/config

  .. note::

        Lexicon will look for two types of configuration files in the provided path to ``--config-dir``
        (current workdir by default): a general configuration file named ``lexicon.yml`` and a provider-specific
        configuration file named ``lexicon_[PROVIDER_NAME].yml``.

        For a general configuration file, provider options need be set under a key named after the provider:

        .. code-block:: yaml

            # /path/to/config/lexicon.yml
            clouflare:
              auth_token: YOUR_TOKEN

        For a provider-specific configuration file, provider options need to be set at the root:

        .. code-block:: yaml

            # /path/to/config/lexicon_cloudflare.yml
            auth_token: YOUR_TOKEN

Passing general options to Lexicon
==================================

General options are options not specific to a provider, like ``delegated``. They can be passed like
the provider options (by CLI, by environment variable or by configuration file). Please note that for
configuration file, options will be set at the root, and cannot be set in provider-specific configuration files.

.. code-block:: yaml

    # /path/to/config/lexicon.yml
    delegated: domain.net
    cloudflare:
      ...

The ``auto`` provider
=====================

The ``auto`` provider is a special provider. It resolves dynamically the actual provider to use based on the
domain provided to Lexicon. To do so, it resolves the nameservers that serves the DNS zone for this domain,
and find the relevant DNS provider based on an internal map that associate each DNS provider to its known
nameservers.

Basically if ``domain.net`` is served by CloudFlare, and a TXT entry needs to be inserted in this domain,
you can use the following command:

.. code-block:: bash

    lexicon auto create domain.net TXT --name foo --content bar

The options specific to the actual provider that will be used still need to be set, by CLI flag, environment
variable or configuration file. However for CLI, the option name will be prefixed with ``[ACTUAL_PROVIDER]-``
when passed to ``auto``. For instance, the ``auth_token`` option for ``cloudflare`` will be passed
using ``--cloudflare-auth-token``.
