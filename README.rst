============
|logo_named|
============

Manipulate DNS records on various DNS providers in a standardized/agnostic way.

|build_status| |coverage_status| |docker_pulls| |pypy_version| |pypy_python_support| |github_license|

.. |logo_named| image:: https://raw.githubusercontent.com/AnalogJ/lexicon/master/docs/images/logo_named.svg
    :alt: Lexicon

.. |build_status| image:: https://dev.azure.com/AnalogJ/lexicon/_apis/build/status/AnalogJ.lexicon?branchName=master
    :target: https://dev.azure.com/AnalogJ/lexicon/_build/latest?definitionId=1&branchName=master

.. |coverage_status| image:: https://coveralls.io/repos/github/AnalogJ/lexicon/badge.svg
    :target: https://coveralls.io/github/AnalogJ/lexicon?branch=master

.. |docker_pulls| image:: https://img.shields.io/docker/pulls/analogj/lexicon.svg
    :target: https://hub.docker.com/r/analogj/lexicon

.. |pypy_version| image:: https://img.shields.io/pypi/v/dns-lexicon.svg
    :target: https://pypi.python.org/pypi/dns-lexicon

.. |pypy_python_support| image:: https://img.shields.io/pypi/pyversions/dns-lexicon.svg
    :target: https://pypi.python.org/pypi/dns-lexicon

.. |github_license| image:: https://img.shields.io/github/license/AnalogJ/lexicon.svg
    :target: https://github.com/AnalogJ/lexicon/blob/master/LICENSE

.. contents:: Table of Contents
   :local:

.. tag:intro-begin

Why using Lexicon?
==================

Lexicon provides a way to manipulate DNS records on multiple DNS providers in a standardized way.

Lexicon can be used as:

- a CLI tool:

.. code-block:: bash

    # Create a TXT entry in domain.net zone hosted by CloudFlare
    lexicon cloudflare create domain.net TXT --name foo --content bar

- or a Python library:

.. code-block:: python

    # Create a TXT entry in domain.net zone hosted by CloudFlare
    from lexicon.client import Client
    from lexicon.config import ConfigResolver

    action = {
        "provider_name" : "cloudflare",
        "action": "create",
        "domain": "domain.net",
        "type": "TXT",
        "name": "foo",
        "content": "bar",
    }
    config = ConfigResolver().with_env().with_dict(action)
    Client(config).execute()

Lexicon was designed to be used in automation, specifically letsencrypt.

* `Generating Intranet & Private Network SSL Certificates using Lets Encrypt & Lexicon <http://blog.thesparktree.com/post/138999997429/generating-intranet-and-private-network-ssl>`_

Supported providers
===================

Only DNS providers who have an API can be supported by `lexicon`.

The current supported providers are:

- `Aliyun.com <https://help.aliyun.com/document_detail/29739.html>`_
- `AuroraDNS <https://www.pcextreme.com/aurora/dns>`_
- `AWS Route53 <https://docs.aws.amazon.com/Route53/latest/APIReference/Welcome.html>`_
- `Azure DNS <https://docs.microsoft.com/en-us/rest/api/dns/>`_
- `Cloudflare <https://api.cloudflare.com/#endpoints>`_
- `ClouDNS <https://www.cloudns.net/wiki/article/56/>`_
- `CloudXNS <https://www.cloudxns.net/Support/lists/cid/17.html>`_
- `ConoHa <https://www.conoha.jp/docs/>`_
- `Constellix <https://api-docs.constellix.com/?version=latest>`_
- `DigitalOcean <https://developers.digitalocean.com/documentation/v2/#create-a-new-domain>`_
- `Dinahosting <https://en.dinahosting.com/api>`_
- `DirectAdmin <https://www.directadmin.com/features.php?id=504>`_
- DNSimple `v1 <https://developer.dnsimple.com/>`_, `v2 <https://developer.dnsimple.com/v2/>`_
- `DnsMadeEasy <https://api-docs.dnsmadeeasy.com/?version=latest>`_
- `DNSPark <https://dnspark.zendesk.com/entries/31210577-REST-API-DNS-Documentation>`_
- `DNSPod <https://support.dnspod.cn/Support/api>`_
- `Dreamhost <https://help.dreamhost.com/hc/en-us/articles/217560167-API_overview>`_
- `Dynu <https://www.dynu.com/Support/API>`_
- `EasyDNS <http://docs.sandbox.rest.easydns.net/>`_
- `Easyname <https://www.easyname.com/en>`_
- `EUserv <https://support.euserv.com/api-doc/>`_
- `ExoScale <https://community.exoscale.com/documentation/dns/api/>`_
- Gandi `RPC (old) <http://doc.rpc.gandi.net>`_ / `LiveAPI <http://doc.livedns.gandi.net/>`_
- `Gehirn <https://support.gehirn.jp/apidocs/gis/dns/index.html>`_
- `Glesys <https://github.com/glesys/API/wiki/>`_
- `GoDaddy <https://developer.godaddy.com/getstarted#access>`_
- `Google Cloud DNS <https://cloud.google.com/dns/api/v1/>`_
- `Gransy (sites subreg.cz, regtons.com and regnames.eu) <https://subreg.cz/manual/>`_
- `Hover <https://hoverapi.docs.apiary.io/>`_
- `Hurricane Electric DNS <https://dns.he.net/>`_
- `Hetzner <https://dns.hetzner.com/api-docs/>`_
- `Infoblox <https://docs.infoblox.com/display/ILP/Infoblox+Documentation+Portal>`_
- `Infomaniak <https://www.infomaniak.com>`_
- `Internet.bs <https://internetbs.net/ResellerRegistrarDomainNameAPI>`_
- `INWX <https://www.inwx.de/en/offer/api>`_
- `Joker.com <https://joker.com/faq/index.php?action=show&cat=39>`_
- `Linode <https://www.linode.com/api/dns>`_
- `Linode v4 <https://developers.linode.com/api/docs/v4#tag/Domains>`_
- `LuaDNS <http://www.luadns.com/api.html>`_
- `Memset <https://www.memset.com/apidocs/methods_dns.html>`_
- `Mythic Beasts (v2 API) <https://www.mythic-beasts.com/support/api/dnsv2>`_
- `Njalla <https://njal.la/api/>`_
- `Namecheap <https://www.namecheap.com/support/api/methods.aspx>`_
- `Namesilo <https://www.namesilo.com/api_reference.php>`_
- `Netcup <https://ccp.netcup.net/run/webservice/servers/endpoint.php>`_
- NFSN (NearlyFreeSpeech)
- `NS1 <https://ns1.com/api/>`_
- `OnApp <https://docs.onapp.com/display/55API/OnApp+5.5+API+Guide>`_
- Online
- `OVH <https://api.ovh.com/>`_
- `Plesk <https://docs.plesk.com/en-US/onyx/api-rpc/about-xml-api.28709/>`_
- `PointHQ <https://pointhq.com/api/docs>`_
- `PowerDNS <https://doc.powerdns.com/md/httpapi/api_spec/>`_
- `Rackspace <https://developer.rackspace.com/docs/cloud-dns/v1/developer-guide/>`_
- `Rage4 <https://gbshouse.uservoice.com/knowledgebase/articles/109834-rage4-dns-developers-api>`_
- `RcodeZero <https://my.rcodezero.at/api-doc>`_
- `RFC2136 <https://en.wikipedia.org/wiki/Dynamic_DNS>`_
- `Sakura Cloud by SAKURA Internet Inc. <https://developer.sakura.ad.jp/cloud/api/1.1/>`_
- `SafeDNS by UKFast <https://developers.ukfast.io/documentation/safedns>`_
- `SoftLayer <https://sldn.softlayer.com/article/REST#HTTP_Request_Types>`_
- `Transip <https://www.transip.nl/transip/api/>`_
- `UltraDNS <https://ultra-portalstatic.ultradns.com/static/docs/REST-API_User_Guide.pdf>`_
- `Vercel <https://vercel.com/docs/api#endpoints/dns>`_
- `Vultr <https://www.vultr.com/api/#tag/dns>`_
- `Yandex <https://tech.yandex.com/domain/doc/reference/dns-add-docpage/>`_
- `Zilore <https://zilore.com/en/help/api>`_
- `Zonomi <http://zonomi.com/app/dns/dyndns.jsp>`_

.. tag:intro-end

Documentation
=============

Online documentation (user guide, configuration reference) is available in the `Lexicon documentation`_.

For a quick start, please have a look in particular at the `User guide`_.

.. _Lexicon documentation: https://dns-lexicon.readthedocs.io
.. _User guide: https://dns-lexicon.readthedocs.io/en/latest/user_guide.html

Contributing
============

If you want to help in the Lexicon development, you are welcome!

Please have a look at the `Developer guide`_ page to know how to start.

.. _Developer guide: https://dns-lexicon.readthedocs.io/en/latest/developer_guide.html

Licensing
=========

- MIT
- Logo_: transform by Mike Rowe from the Noun Project

.. _Logo: https://thenounproject.com/term/transform/397964
