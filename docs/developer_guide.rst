===============
Developer guide
===============

Thanks! There are tons of different DNS services, and unfortunately a large portion of them require
paid accounts, which makes it hard for us to develop ``lexicon`` providers on our own. We want to keep
it as easy as possible to contribute to ``lexicon``, so that you can automate your favorite DNS service.
There are a few guidelines that we need contributors to follow so that we can keep on top of things.

Potential providers
===================

Potential providers are as follows. If you would like to contribute one, please follow the
current document instructions and open a pull request.

- `AHNames <https://ahnames.com/en/resellers?tab=2>`_
- `DurableDNS <https://durabledns.com/wiki/doku.php/ddns>`_ (?? Can't set TXT records ??)
- cyon.ch
- `Dyn <https://help.dyn.com/dns-api-knowledge-base/>`_ ($$ requires paid account $$)
- `EntryDNS <https://entrydns.net/help>`_ ($$ requires paid account $$)
- `FreeDNS <https://freedns.afraid.org/scripts/freedns.clients.php>`_
- `Host Virtual DNS <https://github.com/hostvirtual/hostvirtual-python-sdk/blob/master/hostvirtual.py>`_ ($$ requires paid account $$)
- HostEurope
- Infoblox NIOS
- `ironDNS <https://www.irondns.net/download/soapapiguide.pdf;jsessionid=02A1029AA9FB8BACD2048A60F54668C0>`_ ($$ requires paid account $$)
- ISPConfig
- `InternetX autoDNS <https://internetx.com>`_
- Knot DNS
- KingHost
- `Liquidweb <https://www.liquidweb.com/storm/api/docs/v1/Network/DNS/Zone.html>`_ ($$ requires paid account $$)
- `Loopia <https://www.loopia.com/api/>`_ ($$ requires paid account $$)
- `Mythic Beasts <https://www.mythic-beasts.com/support/api/primary>`_
- `NFSN (NearlyFreeSpeech) <https://api.nearlyfreespeech.net/>`_ ($$ requires paid account $$)
- `RFC2136 <https://en.wikipedia.org/wiki/Dynamic_DNS>`_
- `Servercow <https://servercow.de>`_
- selectel.com
- `TELE3 <https://www.tele3.cz>`_
- `UltraDNS <https://restapi.ultradns.com/v1/docs>`_ ($$ requires paid account $$)
- UnoEuro API
- VSCALE
- `WorldWideDns <https://www.worldwidedns.net/dns_api_protocol.asp>`_ ($$ requires paid account $$)
- `Zerigo <https://www.zerigo.com/managed-dns/rest-api>`_ ($$ requires paid account $$)
- `Zoneedit <http://forum.zoneedit.com/index.php?threads/dns-update-api.419/>`_
- **Any others I missed**

Setup a development environment
===============================

Fork, then clone the repo:

.. code-block:: bash

    $ git clone git@github.com:your-username/lexicon.git

Install Poetry if you not have it already:

.. code-block:: bash

    $ curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python

Configure the virtual environment with full providers support and activate it:

.. code-block:: bash

    $ cd lexicon
    $ poetry install -E full
    $ source .venv/bin/activate

Make sure the tests pass:

.. code-block:: bash

    $ tox -e standard

You can test a specific provider using:

.. code-block:: bash

    $ pytest lexicon/tests/providers/test_foo.py

.. note::

    Please note that by default, tests are replayed from recordings located in
    ``tests/fixtures/cassettes``, not against the real DNS provider APIs.

Adding a new DNS provider
=========================

Now that you have a working development environment, lets add a new provider.
Internally lexicon does a bit of magic to wire everything together, so the only
thing you'll really need to do is is create the following file.

 - ``lexicon/providers/foo.py``

Where ``foo`` should be replaced with the name of the DNS service in lowercase
and without spaces or special characters (eg. ``cloudflare``)

Your provider file should contain 3 things:

- a ``NAMESERVER_DOMAINS`` which contains the domain(s) used by the DNS provider nameservers FQDNs
  (eg. Google Cloud DNS uses nameservers that have the FQDN pattern ``ns-cloud-cX-googledomains.com``,
  so ``NAMESERVER_DOMAINS`` will be ``['googledomains.com']``).

- a ``provider_parser`` which is used to add provider specific commandline arguments.
  eg. If you define two cli arguments: ``--auth-username`` and ``--auth-token``,
  those values will be available to your provider via ``self._get_provider_option('auth_username')``
  or ``self._get_provider_option('auth_token')`` respectively

- a ``Provider`` class which inherits from BaseProvider_, which is in the ``base.py`` file.
  The BaseProvider_ defines the following functions, which must be overridden in your
  provider implementation:

  - ``_authenticate``
  - ``_create_record``
  - ``_list_records``
  - ``_update_record``
  - ``_delete_record``
  - ``_request``

  It also provides a few helper functions which you can use to simplify your implementation.
  See the `cloudflare.py`_ file, or any provider in the `lexicon/providers/`_ folder for examples

It's a good idea to review the `provider specification`_ to ensure that your interface follows
the proper conventions.

.. note::

    Please keep in mind the following:

    - ``lexicon`` is designed to work with multiple versions of python. That means
      your code will be tested against python 3.6 and 3.8 on Windows, Linux and Mac OS X.
    - any provider specific dependencies should be added to the ``setup.py`` file,
      under the ``extra_requires`` heading. The group name should be the name of the
      provider. eg:

    .. code-block:: python

        extras_require={
            'route53': ['boto3']
        }

.. _BaseProvider: https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py
.. _cloudflare.py: https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/cloudflare.py
.. _lexicon/providers/: https://github.com/AnalogJ/lexicon/tree/master/lexicon/providers
.. _provider specification: https://dns-lexicon.readthedocs.io/en/latest/provider_specification.html

Testing your provider
=====================

Test against the live API
-------------------------

First let's validate that your provider shows up in the CLI.

.. code-block:: bash

    $ lexicon foo --help

If everything worked correctly, you should get a help page that's specific
to your provider, including your custom optional arguments.

Now you can run some manual commands against your provider to verify that
everything works as you expect.

.. code-block:: bash

    $ lexicon foo list example.com TXT
    $ lexicon foo create example.com TXT --name demo --content "fake content"

Once you're satisfied that your provider is working correctly, we'll run the
integration test suite against it, and verify that your provider responds the
same as all other ``lexicon`` providers. ``lexicon`` uses ``vcrpy`` to make recordings
of actual HTTP requests against your DNS service's API, and then reuses those
recordings during testing.

The only thing you need to do is create the following file:

 - ``lexicon/tests/providers/test_foo.py``

Then you'll need to populate it with the following template:

.. code-block:: python

    # Test for one implementation of the interface
    from lexicon.tests.providers.integration_tests import IntegrationTestsV2
    from unittest import TestCase

    # Hook into testing framework by inheriting unittest.TestCase and reuse
    # the tests which *each and every* implementation of the interface must
    # pass, by inheritance from integration_tests.IntegrationTests
    class FooProviderTests(TestCase, IntegrationTestsV2):
        """Integration tests for Foo provider"""
        provider_name = 'foo'
        domain = 'example.com'
        def _filter_post_data_parameters(self):
            return ['login_token']

        def _filter_headers(self):
            return ['Authorization']

        def _filter_query_parameters(self):
            return ['secret_key']

        def _filter_response(self, response):
            """See `IntegrationTests._filter_response` for more information on how
            to filter the provider response."""
            return response

Make sure to replace any instance of ``foo`` or ``Foo`` with your provider name.
``domain`` should be a real domain registered with your provider (some providers
have a sandbox/test environment which doesn't require you to validate ownership).

The ``_filter_*`` methods ensure that your credentials are not included in the
``vcrpy`` recordings that are created. You can take a look at recordings for other
providers, they are stored in the `tests/fixtures/cassettes/`_ sub-folders.

Then you'll need to setup your environment variables for testing. Unlike running
``lexicon`` via the CLI, the test suite cannot take user input, so we'll need to provide
any CLI arguments containing secrets (like ``--auth-*``) using environmental variables
prefixed with ``LEXICON_FOO_``.

For instance, if you had a ``--auth-token`` CLI argument, you can populate it
using the ``LEXICON_FOO_AUTH_TOKEN`` environmental variable.

Notice also that you should pass any required non-secrets arguments programmatically using the
``_test_parameters_override()`` method. See `test_powerdns.py`_ for an example.

.. _tests/fixtures/cassettes/: https://github.com/AnalogJ/lexicon/tree/master/tests/fixtures/cassettes
.. _test_powerdns.py: https://github.com/AnalogJ/lexicon/blob/5ee4d16f9d6206e212c2197f2e53a1db248f5eb9/lexicon/tests/providers/test_powerdns.py#L19

Test recordings
---------------

Now you need to run the ``py.test`` suite again, but in a different mode: the live tests mode.
In default test mode, tests are replayed from existing recordings. In live mode, tests are executed
against the real DNS provider API, and recordings will automatically be generated for your provider.

To execute the ``py.test`` suite using the live tests mode, execute py.test with the environment
variable ``LEXICON_LIVE_TESTS`` set to ``true`` like below:

.. code-block:: bash

	LEXICON_LIVE_TESTS=true pytest lexicon/tests/providers/test_foo.py

If any of the integration tests fail on your provider, you'll need to delete the recordings that
were created, make your changes and then try again.

.. code-block:: bash

    rm -rf tests/fixtures/cassettes/foo/IntegrationTests

Once all your tests pass, you'll want to double check that there is no sensitive data in the
``tests/fixtures/cassettes/foo/IntegrationTests`` folder, and then ``git add`` the whole folder.

.. code-block:: bash

    git add tests/fixtures/cassettes/foo/IntegrationTests

Finally, push your changes to your Github fork, and open a PR.

Skipping Tests/Suites
---------------------

Neither of the snippets below should be used unless necessary. They are only included
in the interest of documentation.

In your ``lexicon/tests/providers/test_foo.py`` file, you can use ``@pytest.mark.skip`` to skip
any individual test that does not apply (and will never pass)

.. code-block:: python

    @pytest.mark.skip(reason="can not set ttl when creating/updating records")
    def test_provider_when_calling_list_records_after_setting_ttl(self):
        return

You can also skip extended test suites by inheriting your provider test class from ``IntegrationTestsV1``
instead of ``IntegrationTestsV2``:

.. code-block:: python

    from lexicon.tests.providers.integration_tests import IntegrationTestsV1
    from unittest import TestCase

    class FooProviderTests(TestCase, IntegrationTestsV1):
        """Integration tests for Foo provider"""

CODEOWNERS file
===============

Next, you should add yourself to the `CODEOWNERS file`_, in the root of the repo.
It's my way of keeping track of who to ping when I need updated recordings as the
test suites expand & change.

.. _CODEOWNERS file: https://github.com/AnalogJ/lexicon/blob/master/CODEOWNERS

TODO list
=========

- [x] Create and Register a lexicon pip package.
- [ ] Write documentation on supported environmental variables.
- [x] Wire up automated release packaging on PRs.
- [x] Check for additional dns hosts with apis (from fog_, dnsperf_, libcloud_)
- [ ] Get a list of Letsencrypt clients, and create hook files for them `letsencrypt clients`_

.. _fog: http://fog.io/about/provider_documentation.html
.. _dnsperf: http://www.dnsperf.com/
.. _libcloud: https://libcloud.readthedocs.io/en/latest/dns/supported_providers.html
.. _letsencrypt clients: https://github.com/letsencrypt/letsencrypt/wiki/Links
