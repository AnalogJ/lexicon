==========
User guide
==========

Installation
============

.. warning::

    It is strongly advised with pip to install Lexicon in a Python virtual environment,
    in order to avoid interference between Python modules preinstalled on your system as
    OS packages and modules installed by pip (see https://docs.python-guide.org/dev/virtualenvs/).

To use lexicon as a CLI application, do the following:

.. code-block:: bash

    $ pip install dns-lexicon

Some providers (like Route53 and TransIP) require additional dependencies. You can install
the `provider specific dependencies`_ separately:

.. _provider specific dependencies: https://github.com/AnalogJ/lexicon/blob/master/setup.py#L34-L44

.. code-block:: bash

    $ pip install dns-lexicon[route53]

To install lexicon with the additional dependencies of every provider, do the following:

.. code-block:: bash

    $ pip install dns-lexicon[full]

You can also install the latest version from the repository directly.

.. code-block:: bash

    $ pip install git+https://github.com/AnalogJ/lexicon.git

and with Route 53 provider dependencies:

.. code-block:: bash

    $ pip install git+https://github.com/AnalogJ/lexicon.git#egg=dns-lexicon[route53]

.. note::

    As an alternative you can also install Lexicon using the OS packages available for major
    Linux distributions (see `lexicon` or `dns-lexicon` package in https://pkgs.org/download/lexicon).

Usage
=====

.. code-block:: bash

    $ lexicon -h
      usage: lexicon [-h] [--version] [--delegated DELEGATED]
                     {cloudflare,cloudxns,digitalocean,dnsimple,dnsmadeeasy,dnspark,dnspod,easydns,luadns,namesilo,nsone,pointhq,rage4,route53,vultr,yandex,zonomi}
                     ...

      Create, Update, Delete, List DNS entries

      positional arguments:
        {cloudflare,cloudxns,digitalocean,dnsimple,dnsmadeeasy,dnspark,dnspod,easydns,luadns,namesilo,nsone,pointhq,rage4,route53,vultr,yandex,zonomi}
                              specify the DNS provider to use
          cloudflare          cloudflare provider
          cloudxns            cloudxns provider
          digitalocean        digitalocean provider
        ...
          rage4               rage4 provider
          route53             route53 provider
          vultr               vultr provider
          yandex              yandex provider
          zonomi              zonomi provider

      optional arguments:
        -h, --help            show this help message and exit
        --version             show the current version of lexicon
        --delegated DELEGATED
                              specify the delegated domain


      $ lexicon cloudflare -h
      usage: lexicon cloudflare [-h] [--name NAME] [--content CONTENT] [--ttl TTL]
                                [--priority PRIORITY] [--identifier IDENTIFIER]
                                [--auth-username AUTH_USERNAME]
                                [--auth-token AUTH_TOKEN]
                                {create,list,update,delete} domain
                                {A,AAAA,CNAME,MX,NS,SPF,SOA,TXT,SRV,LOC}

      positional arguments:
        {create,list,update,delete}
                              specify the action to take
        domain                specify the domain, supports subdomains as well
        {A,AAAA,CNAME,MX,NS,SPF,SOA,TXT,SRV,LOC}
                              specify the entry type

      optional arguments:
        -h, --help            show this help message and exit
        --name NAME           specify the record name
        --content CONTENT     specify the record content
        --ttl TTL             specify the record time-to-live
        --priority PRIORITY   specify the record priority
        --identifier IDENTIFIER
                              specify the record for update or delete actions
        --auth-username AUTH_USERNAME
                              specify email address used to authenticate
        --auth-token AUTH_TOKEN
                              specify token used authenticate

                              specify the entry type

      optional arguments:
        -h, --help            show this help message and exit
        --name NAME           specify the record name
        --content CONTENT     specify the record content
        --ttl TTL             specify the record time-to-live
        --priority PRIORITY   specify the record priority
        --identifier IDENTIFIER
                              specify the record for update or delete actions
        --auth-username AUTH_USERNAME
                              specify email address used to authenticate
        --auth-token AUTH_TOKEN
                              specify token used authenticate

Using the lexicon CLI is pretty simple:

.. code-block:: bash

    # setup provider environmental variables:
    export LEXICON_CLOUDFLARE_USERNAME="myusername@example.com"
    export LEXICON_CLOUDFLARE_TOKEN="cloudflare-api-token"

    # list all TXT records on cloudflare
    lexicon cloudflare list example.com TXT

    # create a new TXT record on cloudflare
    lexicon cloudflare create www.example.com TXT --name="_acme-challenge.www.example.com." --content="challenge token"

    # delete a  TXT record on cloudflare
    lexicon cloudflare delete www.example.com TXT --name="_acme-challenge.www.example.com." --content="challenge token"
    lexicon cloudflare delete www.example.com TXT --identifier="cloudflare record id"

Configuration
=============

Authentication
--------------

Most supported DNS services provide an API token, however each service implements authentication differently.
Lexicon attempts to standardize authentication around the following CLI flags:

- ``--auth-username`` - For DNS services that require it, this is usually the account id or email address
- ``--auth-password`` - For DNS services that do not provide an API token, this is usually the account password
- ``--auth-token`` - This is the most common auth method, the API token provided by the DNS service

You can see all the ``--auth-*`` flags for a specific service by reading the DNS service specific help:
``lexicon cloudflare -h``

Environmental variables
-----------------------

Instead of providing authentication information via the CLI, you can also specify them via environmental
variables. Every DNS service and auth flag maps to an environmental variable as follows:
``LEXICON_{DNS Provider Name}_{Auth Type}``

So instead of specifying ``--auth-username`` and ``--auth-token`` flags when calling ``lexicon cloudflare ...``,
you could instead set the ``LEXICON_CLOUDFLARE_USERNAME`` and ``LEXICON_CLOUDFLARE_TOKEN`` environmental variables.

If you've got a subdomain delegation configured and need records configured within that
(eg, you're trying to set ``test.foo.example.com`` where ``foo.example.com`` is configured as a separate zone),
set ``LEXICON_DELEGATED`` to the delegated domain.

.. code-block:: bash

    LEXICON_DELEGATED=foo.example.com

TLD cache
---------

The tldextract_ library is used by Lexicon to find the actual domain name from the provided FQDN
(eg. ``domain.net`` is the actual domain in ``www.domain.net``). Lexicon stores ``tldextract`` cache
by default in ``~/.lexicon_tld_set`` where ``~`` is the current user's home directory. You can change
this path using the ``LEXICON_TLDEXTRACT_CACHE`` environment variable.

For instance, to store ``tldextract`` cache in ``/my/path/to/tld_cache``, you can invoke Lexicon
like this from a Linux shell:

.. code-block:: bash

    LEXICON_TLDEXTRACT_CACHE=/my/path/to/tld_cache lexicon myprovider create www.example.net TXT ...

.. _tldextract: https://pypi.org/project/tldextract/

Integration
===========

Lexicon can be integrated with various tools and process to help handling DNS records.

Let'sEncrypt instructions
-------------------------

Lexicon has an example `dehydrated hook file`_ that you can use for any supported provider.
All you need to do is set the PROVIDER env variable.

.. code-block:: bash

    PROVIDER=cloudflare dehydrated --cron --hook dehydrated.default.sh --challenge dns-01

Lexicon can also be used with Certbot_ and the included `Certbot hook file`_ (requires configuration).

.. _dehydrated hook file: examples/dehydrated.default.sh
.. _Certbot: https://certbot.eff.org/
.. _Certbot hook file: examples/certbot.default.sh

Docker
------

There is an included example Dockerfile that can be used to automatically generate certificates for your website.
