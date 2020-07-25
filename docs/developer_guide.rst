===============
Developer guide
===============

Thanks! There are tons of different DNS services, and unfortunately a large portion of them require
paid accounts, which makes it hard for us to develop ``lexicon`` providers on our own. We want to keep
it as easy as possible to contribute to ``lexicon``, so that you can automate your favorite DNS service.
There are a few guidelines that we need contributors to follow so that we can keep on top of things.

Setup a development environment
===============================

Fork, then clone the repo:

.. code-block:: bash

    $ git clone git@github.com:your-username/lexicon.git

Create a python virtual environment:

.. code-block:: bash

    $ virtualenv -p python2.7 venv
    $ source venv/bin/activate

Install `lexicon` in development mode with full providers support:

.. code-block:: bash

    $ pip install -e .[full,dev]

Make sure the tests pass:

.. code-block:: bash

    $ py.test lexicon/tests

You can test a specific provider using:

.. code-block:: bash

    $ py.test lexicon/tests/providers/test_foo.py

.. note::

    Please note that by default, tests are replayed from recordings located in
    ``tests/fixtures/cassettes``, not against the real DNS provider APIs.

Adding a new DNS provider
=========================

Now that you have a working development environment, lets add a new provider.
Internally lexicon does a bit of magic to wire everything together, so the only
thing you'll really need to do is is create the following file.

 - ``lexicon/providers/foo.py``

Where `foo` should be replaced with the name of the DNS service in lowercase
and without spaces or special characters (eg. ``cloudflare``)

Your provider file should contain 3 things:

- a `NAMESERVER_DOMAINS` which contains the domain(s) used by the DNS provider nameservers FQDNs
(eg. Google Cloud DNS uses nameservers that have the FQDN pattern `ns-cloud-cX-googledomains.com`,
so `NAMESERVER_DOMAINS` will be `['googledomains.com']`).

- a `provider_parser` which is used to add provider specific commandline arguments.
eg. If you define two cli arguments: `--auth-username` and `--auth-token`,
 those values will be available to your provider via `self._get_provider_option('auth_username')`
 or `self._get_provider_option('auth_token')` respectively

- a `Provider` class which inherits from [`BaseProvider`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py), which is in the `base.py` file.
The [`BaseProvider`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py)
defines the following functions, which must be overridden in your provider implementation:

    - `_authenticate`
    - `_create_record`
    - `_list_records`
    - `_update_record`
    - `_delete_record`
    - `_request`

	It also provides a few helper functions which you can use to simplify your implemenation.
	See the [`cloudflare.py`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/cloudflare.py)
	 file, or any provider in the [`lexicon/providers/`](https://github.com/AnalogJ/lexicon/tree/master/lexicon/providers) folder for examples

It's a good idea to review the provider [specification](https://github.com/AnalogJ/lexicon/blob/master/SPECIFICATION.md) to ensure that your interface follows
the proper conventions.

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
