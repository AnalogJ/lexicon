# Changelog

## master - CURRENT
### Modified migrate build tooling from poetry to uv

## 3.18.0 - 22/08/2024
### Added
* Add `timeweb` provider (#1850)
* Add `qcloud` provider (#1824)

### Modified
* Update cloudflare documentation regarding the zoneID (#1783)
* Add support of personal access tokens (PATs) in `gandi` provider (#1987)
* Prevent invalid TTL values and proper behavior with subdomains in `godaddy` provider (#1834)

## 3.17.0 - 06/11/2023
### Added
* New method to determine the actual zone name for a given FQDN. Historically it was an extraction
  of the second-level domain given well-known TLDs (eg., `domain.net` for `www.domain.net`) using
  `tldextract`, and usage of `--delegated` option to enforce a specific zone name that is useful for
  third-level domains hosted on a specific zone (eg., sub-zone `sub.domain.net` delegated from zone
  `domain.net`).
  It is now possible to use the `--resolve-zone-name` flag on Lexicon client to trigger an actual
  resolution of the zone name from a given FQDN using live DNS servers by leveraging `dnspython`
  utilities. Most of the time this makes `--delegated` useless, since Lexicon will be able to guess
  the correct zone name.

## 3.16.1 - 18/10/2023
### Added
* Add support to Python 3.12.

### Modified
* Support older versions of requests (<2.27.0) in `ovh` provider.

## 3.16.0 - 14/10/2023
### Removed
* Drop support for Python 3.7

## 3.15.1 - 13/10/2023
### Modified
* Protect `ovh` provider against invalid response bodies
  that are returned sometimes by OVH APIs.
* Fix filtering by record content in `godaddy` provider.

## 3.15.0 - 30/09/2023
### Added
* Add `pyotp` Python dependency in Lexicon to help implementing OTP (one-time password)
  on providers whose API supports this kind of authentication.
* Add OTP support on `hover` provider, with a new flag named `--auth-totp-secret`.
* Add type marker `py.typed` to inform types checkers about availability of type
  annotations in Lexicon codebase.

### Modified
* Fix and modernize ReadTheDoc documentation build.
* Better error management and resource cleanup when `Client` is used as a context manager.

### Removed
* Stop using `cryptography` in providers where only hashing is needed.

## 3.14.1 - 13/08/2023
### Added
* Add back declared support to Python 3.7 for few cycles

## 3.14.0 - 13/08/2023
### Added
* New way to invoke Lexicon as a library: ``lexicon.client.Client`` becomes a context manager.
  When invoked with the `with` keyword, it will provide an operation object that embeds the
  target provider fully authenticated (``authenticate`` method called on the Provider).
  This operation object gives access to four methods: ``create_record``, ``update_record``,
  ``delete_record`` and ``list_records``. These methods can be invoked instead of the old
  ``execute`` method to execute a specific action on the DNS zone. In this case, ``type``,
  ``name``, ``content`` fields do not need to be set in the config anymore, since they are
  passed directly as arguments to the new methods. Upon context manager closing, the ``cleanup``
  method defined in the Provider is ensured to be called. See the README file of the project
  for an example of how to use this new approach.
* Python warnings are emitted from the code to alert about the deprecations listed below.

### Modified
* Former ``NAMESERVER_DOMAIN`` variable and ``provider_parser`` function that had to be defined
  in each provider module are respectively migrated to ``get_nameservers``
  and ``configure_parser`` static methods in each Provider class. They are defined as abstract
  in the interface and must be implemented in the concrete classes.
* Former private methods ``_create_record``, ``_modify_record``, ``_delete_record``
  and ``_list_records`` are migrated to their public counterpart ``create_record``,
  ``modify_record``, ``delete_record`` and ``list_records`` in each Provider class. These are
  the new abstract methods for each action that need to be implemented.
* Method ``lexicon.client.Client.execute`` is deprecated and will be removed in Lexicon 4.
* Package ``lexicon.providers``, containing the actual provider implementations, is migrated to
  ``lexicon._private.providers``. The provider implementations are not supposed to be used
  directly, please use ``lexicon.client.Client`` instead with the new methods described above.
  Package ``lexicon.providers`` stubs to ``lexicon._private.providers`` to ease the migration
  path, but it is deprecated and will be removed in Lexicon 4.
* Module ``lexicon.providers.base``, that contains the Provider interface to implement, is
  migrated to module ``lexicon.interfaces``. Module ``lexicon.providers.base`` stubs
  to ``lexicon.interfaces`` to ease the migration path, but it is deprecated and will be removed
  in Lexicon 4.
* Modules ``lexicon.cli``, ``lexicon.parser`` and ``lexicon.discovery`` are migrated to the
  private package ``lexicon._private`` as they are not part of the public API. Old modules
  stubs to the new modules in the private package ``lexicon._private`` to ease the migration path,
  but it is deprecated and will be removed in Lexicon 4.
* Update documentation, in particular the developer guide, to take into account the new
  architecture of the code to implement a new Provider.
* Functional codebase in ``/lexicon`` folder is moved in ``/src/lexicon`` folder to comply with
  modern Python project layouts. Tests are migrated to ``/tests`` folder.

### Removed
* Drop support for Python 3.7

## 3.13.0 - 07/08/2023
### Added
* Add `wedos` provider (#1675)

### Modified
* Proper handling off authentication errors on `easydns` provider (#1674)
* Allow management of pending (non-active) domains in `cloudflare` provider (#1659)

## 3.12.0 - 11/06/2023
### Added
* Add `duckdns` provider (experimental support) (#1533)
* Add `dnsservices` provider (#1603)
* Add `flexibleengine` provider (#1600)
* Official support for Python 3.11

### Modified
* Upgrade API version used for `azure` provider (#1606)
* Various fixes for documentation (#1488 #1458 #1601 #1605)
* Fix check for extra dependencies (#1568)

## 3.11.7 - 26/10/2022
### Modified
* Fix `easyname` provider (update action) (#1442)

## 3.11.6 - 11/10/2022
### Modified
* Fix `hetzner` provider with large list of entries (#1389)

## 3.11.5 - 10/10/2022
### Modified
* Fix upsertRecordSet in `yandex` provider (#1423)

## 3.11.4 - 11/08/2022
### Modified
* Better management of domain zone id in `yandex` provider (#1338)
* Fix create record action on `glesys` provider (#1356)
* Fix create multiple TXT records for the same name in `azure` provider (#1359)

## 3.11.3 - 21/06/2022
### Added
* Add `porkbun` provider (#1283)

## 3.11.2 - 16/05/2022
### Changed
* Add support of record update without an identifier in `yandex` provider (#1253)

## 3.11.1 - 15/05/2022
### Modified
* Improve the Oracle Cloud DNS (`oci`) provider on the authentication mechanism (#1251)
* Add API documentation to Oracle Cloud DNS (#1247)

## 3.11.0 - 06/05/2022
### Added
* Add `namecom` provider (#1212)

### Modified
* Fix TLD with two parts for `namecheap` provider (#1237)
* Fix `entity__name` parsing in `easyname` provider (#1230)

## 3.10.0 - 01/05/2022
### Added
* Add `--zone-id` CLI flag for `route53` provider
* Add `yandexcloud` provider dedicated to Yandex Cloud solution (#1213)

### Modified
* Improve documentation with auto-generation
* Clarify that `yandex` provider supports Yandex PDD only (#1211)
* Use UUIDs in `aliyun` provider to avoid nonce collisions

## 3.9.5 - 18/04/2022
### Added
* Add `misaka` provider (#1205 #556)

### Modified
* Fix `yandex` provider for MX/SRV records (#1201)
* Fix `joker` provider by using POST requests instead of GET (#1201)

## 3.9.4 - 14/02/2022
### Added
* Add `webgo` provider (#1102)

### Modified
* Extend possible record types list for `dreamhost` provider (#1110)

## 3.9.3 - 27/01/2022
### Modified
* Fix compatibility with requests>=2 in `transip` provider

## 3.9.2 - 17/01/2022
### Modified
* Fix configuration reference

## 3.9.1 - 17/01/2022
### Modified
* Reimplement the `transip` provider using the new REST v6 API

## 3.9.0 - 06/01/2022
## Deleted
* Drop Python 3.6 support

## 3.8.5 - 29/12/2021
### Modified
* Complete redesign of the update and delete actions in GoDaddy provider to fix several issues

## 3.8.4 - 28/12/2021
### Added
* Add the Value Domain provider (#1018)

### Modified
* Fix issue on the GoDaddy provider for update actions

## 3.8.3 - 12/11/2021
### Modified
* Fix `plesk` provider (#1004)
* Update nameservers in `namecheap` provider (#911)

## 3.8.2 - 03/11/2021
### Modified
* Fix `dreamhost` provider since deprecated API endpoints are removed (#998)

## 3.8.1 - 15/10/2021
### Modified
* Fix `rackspace` provider by not sending a body request for `GET` requests (#989)

## 3.8.0 - 04/10/2021
### Modified
* `transip` provider is deprecated and not maintained anymore, it will be replaced
   soon by a new `transip` provider build on top of the TransIP v6 REST API

## Deleted
* `transip` provider is not part of the `full` dns-lexicon extra, you need to install
  explicitly the `transip` extra instead

## 3.7.1 - 04/10/2021
### Modified
* Allow to use newer versions of `cryptography`
* Fix doc about unit tests

## 3.7.0 - 09/08/2021
### Added
* Add the Vercel provider (formerly known as Zeit)
* Add the Oracle Cloud Infrastructure (OCI) DNS provider (#860)

### Modified
* Keep old Zeit provider for compatibility purpose with deprecation notices
* Support multiple domain statuses for Joker provider (#880)

## 3.6.1 - 27/06/2021
### Modified
* Support deprecated `method_whitelist` parameter in urllib3.util.retry.Retry for urllib3<1.26
* Fix support of registered domains for INWX provider (#828)
* Update `mypy` and use external types modules

## 3.6.0 - 02/05/2021
### Added
* Vendor `pynamecheap` project for `namecheap` provider
* Annotate public API with types
* Check mypy types during CI
* Add the RFC2136 DynDNS provider (named `ddns`)
* Use Lexicon specific exceptions in code: `AuthenticationError` for authentication problems

### Modified
* Implement the base provider as an ABC class
* Improve `plesk` provider for wildcard domains or subdomains
* Use `poetry-core` instead of `poetry` for the builds
* Switch to GitHub-native Dependabot

### Deleted
* Remove dependency of `plesk` provider to `xmltodict`
* Remove some Python 2 specific code
* Remove deprecated `type` parameter in providers public methods

## 3.5.6 - 28/03/2021
### Modified
* Migrate Vultr provider to the V2 API (#770)

## 3.5.5 - 20/03/2021
### Added
* Add the Mythic Beasts provider (#739)
* Add the Infomaniak provider (#685 #762)

### Changed
* Improve dev tooling (#761)

## 3.5.4 - 17/03/2021
### Changed
* Support both `tldextract` 2.x and 3.x
* Upgrade third-party dependencies
* Validate PowerDNS provider parameters (#755)
* Support dnspython>=2.1 for `localzone` provider (#760)
* Update Mythic Beasts documentation (#693)
* Fix documentation build and publication

### Deleted
* Remove `mock` and `nose` dependencies (#706)

## 3.5.3 - 02/01/2021
### Modified
* Handle large number of hosted zones in `route53` provider

## 3.5.2 - 23/11/2020
### Modified
* Fix domains in "lock" state with `joker` provider

## 3.5.1 - 16/11/2020
### Added
* Add the Joker.com provider
* Add environment variable `TLDEXTRACT_CACHE_PATH` to configure a tldextract cache custom location for Lexicon

### Modified
* Old environment variable `TLDEXTRACT_CACHE_FILE` is deprecated and will be removed in a future release

## 3.5.0 - 10/11/2020
### Modified
* Avoid installation problems with setuptools==50
* Migrating codebase to Python 3.6+ specific features (Lexicon will explicitly break on older versions now)
* Fix Easyname provider to work with their new website

## 3.4.5 - 02/11/2020
### Added
* Add pagination support to Google Cloud DNS provider (#577)
* Add official support to Python 3.9
* Add SSHFP record support to CloudFlare provider (library only) (#612)

### Modified
* Fix create/update operations when CAA records are presents in GoDaddy provider (#545)
* Fix Hover provider with new authentication URL (#618)

## 3.4.4 - 25/10/2020
### Modified
* Fix Gandi provider to use the new LiveDNS API URL

## 3.4.3 - 07/09/2020
### Modified
* Improve versions constraints by declaring latest major versions known to work with Lexicon

## 3.4.2 - 03/09/2020
### Modified
* Relax versions constraints on Lexicon dependencies until there is a real need.

## 3.4.1 - 21/08/2020
### Added
* Add the Njalla provider

## 3.4.0 - 16/08/2020
### Added
* Use `poetry` to manage dependencies, build and package Lexicon.
* Add integration tests for Mac OS X

### Changed
* The `beautifulsoup4` dependency has been integrated to the core
  ones for generic purpose. As a consequence `henet`, `easyname` and `gratisdns`
  providers do not have optional dependencies anymore.
* Update Docker image to use Python 3.8, and install Lexicon with full extras.

### Removed
* Remove support for Python 2.7.
* Remove support for Python 3.5.
* Remove the extra `security` from `requests` dependency which
  does not make sense anymore on recent versions of Python.

## 3.3.28 - 26/07/2020
### Added
* Redesign of the release process using Azure Pipelines.
* Create a dedicated documentation on ReadTheDoc, refactor README.md into README.rst.

### Changed
* Fix localzone provider to make it work with dnspython 2.x.
* Update easyname provider against the recent API changes.

## 3.3.27 - 08/07/2020
## 3.3.26 - 14/06/2020
## 3.3.25 - 13/06/2020
## 3.3.24 - 02/06/2020
## 3.3.23 - 01/06/2020
## 3.3.22 - 06/05/2020
## 3.3.21 - 06/05/2020
## 3.3.20 - 04/05/2020
## 3.3.19 - 26/03/2020
## 3.3.18 - 17/03/2020
## 3.3.19 - 26/03/2020
## 3.3.18 - 17/03/2020
## 3.3.17 - 14/01/2020
## 3.3.16 - 11/01/2020
## 3.3.15 - 10/01/2020
## 3.3.14 - 08/01/2020
## 3.3.13 - 05/01/2020
## 3.3.12 - 22/12/2019
## 3.3.11 - 04/12/2019
## 3.3.10 - 15/11/2019
## 3.3.9 - 25/10/2019
## 3.3.8 - 25/10/2019
## 3.3.7 - 23/10/2019
## 3.3.6 - 23/10/2019
## 3.3.5 - 22/10/2019
## 3.3.4 - 07/10/2019
## 3.3.3 - 26/08/2019
## 3.3.2 - 25/08/2019
## 3.3.1 - 16/07/2019
## 3.3.0 - 11/07/2019
## 3.2.9 - 28/06/2019
## 3.2.8 - 26/06/2019
## 3.2.7 - 19/06/2019
## 3.2.1 - 04/04/2019
## 3.2.0 - 03/04/2019
## 3.1.7 - 01/04/2019
## 3.1.6 - 06/03/2019
## 3.1.5 - 10/02/2018
## 3.1.4 - 08/02/2019
## 3.1.3 - 06/02/2019
## 3.1.2 - 01/02/2019
## 3.1.1 - 31/01/2019
## 3.1.0 - 30/01/2019
