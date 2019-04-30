"""Module provider for Aliyun"""
from __future__ import absolute_import
import logging
import time
import datetime
import random
import hmac
import sys
from hashlib import sha1
from six.moves import urllib

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['hichina.com']

ALIYUN_DNS_API_ENDPOINT = 'https://alidns.aliyuncs.com'
ALIYUN_DNS_DEFAULT_REGION = 'cn-hangzhou'

def provider_parser(subparser):
    """Module provider for Aliyun"""
    subparser.add_argument(
        "--access-key-id", help="specify api key for authentication")
    subparser.add_argument(
        "--access-secret", help="specify api secret for authentication")


class Provider(BaseProvider):
    """Provider class for Linode"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.client = None

    def _authenticate(self):
        response = self._request('DescribeDomainInfo')

        if 'DomainId' not in response:
            raise Exception(response)

        self.domain_id = response['DomainId']

        return self

    def _create_record(self, rtype, name, content):
        if not self._list_records(rtype, name, content):
            query_params = {
                'Value': content,
                'Type': rtype,
                'RR': self._relative_name(name),
                'TTL': self._get_lexicon_option('ttl')
            }
            self._request('AddDomainRecord', query_params=query_params)

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        query_params = {}

        if rtype:
            query_params['TypeKeyWord'] = rtype

        if name:
            query_params['RRKeyWord'] = self._relative_name(name)

        if content:
            query_params['ValueKeyWord'] = content

        response = self._request('DescribeDomainRecords', query_params=query_params)

        resource_list = response['DomainRecords']['Record']

        processed_records = []
        for resource in resource_list:
            processed_records.append({
                'id': resource['RecordId'],
                'type': resource['Type'],
                'name': self._full_name(resource['RR']),
                'ttl': resource['TTL'],
                'content': resource['Value']
            })
        LOGGER.debug('list_records: %s', processed_records)
        return processed_records

    def __get_record(self, identifier):
        response = self._request('DescribeDomainRecordInfo', query_params={'RecordId': identifier})

        return {
            'id': response['RecordId'],
            'type': response['Type'],
            'name': self._full_name(response['RR']),
            'ttl': response['TTL'],
            'content': response['Value']
        }

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        resources = self._list_records(rtype, name, None)

        for record in resources:
            if (rtype == record['type']) \
                and (self._relative_name(name) == self._relative_name(record['name'])) \
                and (content == record['content']):
                return True

        if not identifier:
            record = resources[0] if resources else None
            identifier = record['id'] if record else None

        if not identifier:
            self._create_record(rtype, name, content)

        LOGGER.debug('update_record: %s', identifier)

        query_params = {'RecordId': identifier}

        if rtype:
            query_params['Type'] = rtype

        if name:
            query_params['RR'] = self._relative_name(name)

        if content:
            query_params['Value'] = content

        query_params['TTL'] = self._get_lexicon_option('ttl')
        self._request('UpdateDomainRecord', query_params=query_params)

        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_resource_id = []
        if not identifier:
            resources = self._list_records(rtype, name, content)
            delete_resource_id = [resource['id'] for resource in resources]
        else:
            delete_resource_id.append(identifier)

        LOGGER.debug('delete_records: %s', delete_resource_id)

        for resource_id in delete_resource_id:
            self._request('DeleteDomainRecord', query_params={'RecordId': resource_id})

        return True

    def _request(self, action='GET', url='/', data=None, query_params=None):
        # force set to the fixed api endpoint
        url = ALIYUN_DNS_API_ENDPOINT

        if query_params is None:
            query_params = {}

        query_params.update(self._build_default_query_params(action))
        query_params.update(self._build_signature_parameters())

        query_params.update({'Signature': self._calculate_signature('GET', query_params)})

        response = requests.request('GET', url, params=query_params)

        # TODO: add exception handle
        return response.json()

    # @param query_params should be {} and not none
    def _calculate_signature(self, http_method, query_params):
        access_secret = self._get_provider_option('access_secret')
        sign_secret = access_secret+'&'

        query_list = list(query_params.items())
        query_list.sort(key=lambda t: t[0])

        canonicalized_query_string = urllib.parse.urlencode(query_list)

        string_to_sign = '&'.join([
            http_method,
            urllib.parse.quote_plus('/'),
            urllib.parse.quote_plus(canonicalized_query_string)])

        signature = ""
        if sys.version_info.major > 2:
            import base64

            sign_secret_bytes = bytes(sign_secret, 'utf-8')
            string_to_sign_bytes = bytes(string_to_sign, 'utf-8')
            sign = hmac.new(sign_secret_bytes, string_to_sign_bytes, sha1)
            signature = base64.b64encode(sign.digest()).decode()
        else:
            sign = hmac.new(sign_secret, string_to_sign, sha1)
            signature = sign.digest().encode('base64').rstrip('\n')

        return signature

    def _build_signature_parameters(self):
        access_key_id = self._get_provider_option('access_key_id')
        signature_nonce = str(int(time.time())) + str(random.randint(1000, 9999))

        return {
            'SignatureMethod': 'HMAC-SHA1',
            'SignatureVersion': '1.0',
            'SignatureNonce': signature_nonce,
            'Timestamp': datetime.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z',
            'AccessKeyId': access_key_id
        }

    def _build_default_query_params(self, action):
        return {
            'Action': action,
            'DomainName': self.domain,
            'Format': 'json',
            'Version': '2015-01-09'
        }
