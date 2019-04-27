"""Module provider for Glesys"""
from __future__ import absolute_import
import json

import requests
from lexicon.providers.base import Provider as BaseProvider


NAMESERVER_DOMAINS = ['glesys.com']


def provider_parser(subparser):
    """Generate a subparser for Glesys"""
    subparser.add_argument(
        "--auth-username", help="specify username (CL12345)")
    subparser.add_argument("--auth-token", help="specify API key")


class Provider(BaseProvider):
    """Provider class for Glesys"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.glesys.com'

    def _authenticate(self):
        payload = self._get('/domain/list')
        domains = payload['response']['domains']
        for record in domains:
            if record['domainname'] == self.domain:
                # Domain records do not have any id.
                # Since domain_id cannot be None, use domain name as id instead.
                self.domain_id = record['domainname']
                break

        if self.domain_id is None:
            raise Exception('No domain found')

    # Create record. If record already exists with the same content, do nothing.
    def _create_record(self, rtype, name, content):
        existing = self.list_records(rtype, name, content)
        if existing:
            # Already exists, do nothing.
            return True

        request_data = {
            'domainname': self.domain,
            'host': self._full_name(name),
            'type': rtype,
            'data': content
        }
        self._addttl(request_data)

        self._post('/domain/addrecord', data=request_data)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(self, rtype=None, name=None, content=None):
        request_data = {
            'domainname': self.domain
        }
        payload = self._post('/domain/listrecords', data=request_data)

        # Convert from Glesys record structure to Lexicon structure.
        processed_records = [self._glesysrecord2lexiconrecord(
            r) for r in payload['response']['records']]

        if rtype:
            processed_records = [
                record for record in processed_records if record['type'] == rtype]
        if name:
            processed_records = [
                record for record in processed_records if record['name'] == self._full_name(name)]
        if content:
            processed_records = [
                record for record in processed_records
                if record['content'].lower() == content.lower()]

        return processed_records

    # Update a record. Identifier must be specified.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        request_data = {'recordid': identifier}
        if name:
            request_data['host'] = name
        if rtype:
            request_data['type'] = rtype
        if content:
            request_data['data'] = content

        self._addttl(request_data)
        self._post('/domain/updaterecord', data=request_data)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        delete_record_id = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            delete_record_id = [record['id'] for record in records]
        else:
            delete_record_id.append(identifier)

        for record_id in delete_record_id:
            request_data = {'recordid': record_id}
            self._post('/domain/deleterecord', data=request_data)

        return True

    # Helpers.
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}

        query_params['format'] = 'json'
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        credentials = (self._get_provider_option('auth_username'),
                       self._get_provider_option('auth_token'))
        response = requests.request(action,
                                    self.api_endpoint + url,
                                    params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers,
                                    auth=credentials)

        # if the request fails for any reason, throw an error.
        response.raise_for_status()
        return response.json()

    # Adds TTL parameter if passed as argument to lexicon.
    def _addttl(self, request_data):
        if self._get_lexicon_option('ttl'):
            request_data['ttl'] = self._get_lexicon_option('ttl')

    # From Glesys record structure: [u'domainname', u'recordid', u'type', u'host', u'ttl', u'data']
    def _glesysrecord2lexiconrecord(self, glesys_record):  # pylint: disable=no-self-use
        return {
            'id': glesys_record['recordid'],
            'type': glesys_record['type'],
            'name': glesys_record['host'],
            'ttl': glesys_record['ttl'],
            'content': glesys_record['data']
        }
