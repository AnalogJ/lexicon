"""Module provider for Aliyun"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.acs_exception.exceptions import ClientException
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordsRequest import DescribeDomainRecordsRequest
from aliyunsdkalidns.request.v20150109.AddDomainRecordRequest import AddDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DeleteDomainRecordRequest import DeleteDomainRecordRequest
from aliyunsdkalidns.request.v20150109.UpdateDomainRecordRequest import UpdateDomainRecordRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainRecordInfoRequest import DescribeDomainRecordInfoRequest
from aliyunsdkalidns.request.v20150109.DescribeDomainInfoRequest import DescribeDomainInfoRequest

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['hichina.com']

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

        access_key_id = self._get_provider_option('access_key_id')
        access_secret = self._get_provider_option('access_secret')

        self.client = AcsClient(access_key_id, access_secret, ALIYUN_DNS_DEFAULT_REGION)

        if self.client is None:
            raise Exception('aliyun authentication failed')

        self.domain_id = self.__fetch_domain_id();       

        return self

    def __fetch_domain_id(self):
        request = DescribeDomainInfoRequest()
        request.set_accept_format('json')
        request.set_DomainName(self.domain)

        response = self.client.do_action_with_exception(request)
        response = json.loads(response)

        if 'DomainId' not in response:
            raise Exception(response['Code'])

        return response['DomainId']



    def _create_record(self, rtype, name, content):
        if not self._list_records(rtype, name, content):
            request = AddDomainRecordRequest()
            request.set_accept_format('json')

            request.set_Value(content)
            request.set_Type(rtype)
            request.set_RR(self._relative_name(name))
            request.set_DomainName(self.domain)
            request.set_TTL(self._get_lexicon_option('ttl'))

            response = self.client.do_action_with_exception(request)

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        request = DescribeDomainRecordsRequest()
        request.set_accept_format('json')

        request.set_DomainName(self.domain)

        if rtype:
            request.set_TypeKeyWord(rtype)

        if name:
            request.set_RRKeyWord(self._relative_name(name))
        
        if content:
            request.set_ValueKeyWord(content)

        response = self.client.do_action_with_exception(request)

        response = json.loads(response)
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
        request = DescribeDomainRecordInfoRequest()
        request.set_accept_format('json')
        request.set_RecordId(identifier)

        response = self.client.do_action_with_exception(request)
        response = json.loads(response)

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
            if (rtype == record['type']) and (self._relative_name(name) == self._relative_name(record['name'])) and (content == record['content']):
                return True

        if not identifier:
            record = resources[0] if resources and len(resources) > 0 else None
            identifier = record['id'] if record else None

        if not identifier:
            self._create_record(rtype, name, content)

        LOGGER.debug('update_record: %s', identifier)

        request = UpdateDomainRecordRequest()
        request.set_accept_format('json')

        request.set_RecordId(identifier)

        if rtype:
            request.set_Type(rtype)

        if name:
            request.set_RR(self._relative_name(name))

        if content:
            request.set_Value(content)

        request.set_TTL(self._get_lexicon_option('ttl'))

        response = self.client.do_action_with_exception(request)

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
            request = DeleteDomainRecordRequest()
            request.set_accept_format('json')

            request.set_RecordId(resource_id)

            response = self.client.do_action_with_exception(request)

        return True