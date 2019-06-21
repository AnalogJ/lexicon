"""Module provider for Dinahosting"""
from __future__ import absolute_import
#import re
import hashlib
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['dinahosting.com']