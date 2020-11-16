# Changelog

## master - CURRENT

## 3.5.1 - 16/11/2020
## Added
* Add the Joker.com provider
* Add environment variable `TLDEXTRACT_CACHE_PATH` to configure a tldextract cache custom location for Lexicon

## Modified
* Old environment variable `TLDEXTRACT_CACHE_FILE` is deprecated and will be removed in a future release

## 3.5.0 - 10/11/2020
## Modified
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
