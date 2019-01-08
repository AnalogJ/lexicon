"""
The Constellix API has some limitations.  We try to paper over them here,
but here's what you need to be aware of:

 1) SOA records are not first-class record types in the Constellix API, so are not supported.
 2) We expect all records to use the "Standard" record type, so failover, pools or round robin with
    failover are not supported.
 3) Because Constellix represents record sets as a single record with multiple values attached,
    not as a set of separate records, create and delete operations end up becoming read/update
    operations when working with record sets.

    Since these aren't atomic operations, it creates a small window where you could have data loss
    if multiple processes were trying to work with the same record set.

    This is unlikely to be a problem in most scenarios, but the possilbity is there.  I've reached
    out to the Constellix folks to see if they have plans to clean up the API to resolve this.
"""
from __future__ import absolute_import
import base64
import hashlib
import hmac
import json
import logging
import time

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['constellix.com']


def provider_parser(subparser):
    """Configure provider parser for Constellix"""
    subparser.add_argument(
        "--auth-username", help="specify the API key username for authentication")
    subparser.add_argument(
        "--auth-token", help="specify secret key for authenticate=")


class Provider(BaseProvider):
    """Provider clss for Constellix"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.domain_details = None
        self.api_endpoint = 'https://api.dns.constellix.com/v1'

    def _authenticate(self):
        try:
            payload = self._get('/domains/')
        except requests.exceptions.HTTPError as error:
            if error.response.status_code == 404:
                payload = {}
            else:
                raise error

        for domain in payload:
            if domain['name'] == self.domain:
                self.domain_id = domain['id']
                self.domain_details = domain
                continue

        if not self.domain_id:
            raise Exception('No domain found')

    # Create record. If record already exists with the same content, do nothing'

    def _create_record(self, rtype, name, content):
        record = {
            'name': self._relative_name(name),
            'ttl': self._get_lexicon_option('ttl'),
            'roundRobin':
                [{'disableFlag': False,
                  'value': content}],
        }
        payload = {}

        try:
            payload = self._post(
                '/domains/{0}/records/{1}/'.format(self.domain_id, rtype), record)
        except requests.exceptions.HTTPError as error:
            # If there is already a record with that name, we need to do an update.
            if error.response.status_code == 400:
                existing_records = self._list_records(rtype=rtype, name=name)
                new_content = [r['content'] for r in existing_records]

                # Only do the update if we are creating a record that doesn't already exist,
                # otherwise Constellix will throw an error.
                if content not in new_content:
                    new_content.append(content)
                    self._update_record(
                        existing_records[0]['id'], rtype=rtype, name=name, content=new_content)
            else:
                raise
        LOGGER.debug('create_record: %s', 'name' in payload)
        return True

    # Currently returns the first value for hosts where there may be multiple
    # values.  Need to check to see how this is handled for other providers.
    def _list_records(self, rtype=None, name=None, content=None):
        return self._list_records_internal(rtype=rtype, name=name, content=content)

    def _list_records_internal(self, rtype=None, name=None, content=None, identifier=None):
        self._check_type(rtype)

        # Oddly, Constellix supports API-level filtering for everything except LOC
        # records, so we need to retrieve all records for LOC and filter based on rtype
        # on our end.
        if not rtype or rtype == 'LOC':
            payload = self._get('/domains/{0}/records/'.format(self.domain_id))
        else:
            payload = self._get(
                '/domains/{0}/records/{1}/'.format(self.domain_id, rtype))

        records = []

        for record in payload:
            for a_record in record['roundRobin']:
                processed_record = {
                    'type': record['type'],
                    'name': '{0}.{1}'.format(record['name'], self.domain),
                    'ttl': record['ttl'],
                    'content': a_record['value'],
                    'id': record['id']
                }

                processed_record = self._clean_TXT_record(processed_record)
                records.append(processed_record)

        records = self._filter_records(
            records, rtype=rtype, name=name, content=content, identifier=identifier)

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        self._check_type(rtype)

        if content and not isinstance(content, (list)):
            content = [content]

        if identifier and (not rtype or not name):
            record = self._list_records_internal(identifier=identifier)
            rtype = record[0]['type']
            name = record[0]['name']
        elif not identifier:
            record = self._list_records(rtype, name)
            identifier = record[0]['id']

        if not identifier:
            raise Exception("No identifier provided")

        data = {
            'id': identifier,
            'ttl': self._get_lexicon_option('ttl'),
            'name': self._relative_name(name)
        }

        data['roundRobin'] = []

        for a_content in content:
            data['roundRobin'].append({'disableFlag': False,
                                       'value': a_content})

        self._put(
            '/domains/{0}/records/{1}/{2}/'.format(self.domain_id, rtype, identifier), data)

        LOGGER.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        self._check_type(rtype)

        records = self._list_records_internal(
            identifier=identifier, rtype=rtype, name=name)

        # If we are filtering delete records by content and we are going to have
        # at least one record left over after deleting, then this becomes an
        # update operation.
        if content:
            current_content = set(r['content'] for r in records)
            if content in current_content and len(current_content) > 1:
                current_content.remove(content)
                self._update_record(
                    records[0]['id'], rtype=rtype, name=name, content=list(current_content))
                return True

        delete_record_id = set(record['id'] for record in records)

        # We need a rtype to do a delete, so pull one from the first record if it's not supplied.
        if not rtype:
            rtype = records[0]['type']

        for record_id in delete_record_id:
            self._delete(
                '/domains/{0}/records/{1}/{2}/'.format(self.domain_id, rtype, record_id))

        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug('delete_record: %s', True)
        return True

    # Helpers
    def _check_type(self, rtype=None):  # pylint: disable=no-self-use
        # Constellix doesn't treat SOA as a separate record type, so we bail on SOA modificiations.
        # It looks like it would be possible to fake SOA CRUD, so an area for possible future
        # improvement

        if rtype == 'SOA':
            raise Exception(
                '{0} record type is not supported in the Constellix Provider'.format(rtype))

        return True

    def _filter_records(self, records, rtype=None, name=None, content=None, identifier=None):  # pylint: disable=too-many-arguments
        _records = []
        for record in records:
            if ((not identifier or record['id'] == identifier) and  # pylint: disable=too-many-boolean-expressions
                    (not rtype or record['type'] == rtype) and
                    (not name or record['name'] == self._full_name(name)) and
                    (not content or record['content'] == content)):
                _records.append(record)
        return _records

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'x-cnsdns-apiKey': self._get_provider_option('auth_username'),
        }
        default_auth = None

        # Date string in epoch format
        request_date = str(int(time.time() * 1000))

        hashed = hmac.new(self._get_provider_option('auth_token').encode(
            'utf-8'), request_date.encode('utf-8'), digestmod=hashlib.sha1)

        default_headers['x-cnsdns-requestDate'] = request_date
        default_headers['x-cnsdns-hmac'] = base64.b64encode(hashed.digest())

        response = requests.request(action, self.api_endpoint + url, params=query_params,
                                    data=json.dumps(data),
                                    headers=default_headers,
                                    auth=default_auth)
        # if the request fails for any reason, throw an error.
        response.raise_for_status()

        # PUT and DELETE actions dont return valid json.
        if action in ['DELETE' or action == 'PUT']:
            return response.text

        return response.json()
