from __future__ import absolute_import
import hashlib
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['godaddy.com']


def ProviderParser(subparser):
    subparser.add_argument(
        '--auth-key', help='specify the key to access the API')
    subparser.add_argument(
        '--auth-secret', help='specify the secret to access the API')


class Provider(BaseProvider):
    """
    Implements the DNS GoDaddy provider.
    Some general remarks about this provider, because it uses a weirdly designed API.
    Indeed, there is no direct way to insert, update or delete a specific record.
    Furthermore, there is no unique identifier for a record.
    Instead GoDaddy use a replace approach: for a given set of records one
    can replace this set with a new set sent through API.
    For the sake of simplicity and consistency across the provider edit methods,
    the set will be always all records in the DNS zone.
    With this approach:
        - adding a record consists in appending a record to the obtained set and call
          replace with the updated set,
        - updating a record consists in modifying a record in the obtained set and call
          replace with the updated set,
        - deleting a record consists in removing a record in the obtained set and call
          replace with the updated set.
    In parallel, as said before, there is no unique identifier.
    This provider then implement a pseudo-identifier, to allow an easy update or delete
    using the '--identifier' lexicon parameter.
    But you need to call the 'list' command just before executing and update/delete action,
    because identifier value is tied to the content of the record, and will change anytime
    something is changed in the record.
    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.api_endpoint = 'https://api.godaddy.com/v1'

    def authenticate(self):
        domain = self.domain

        result = self._get('/domains/{0}'.format(domain))
        self.domain_id = result['domainId']

    def list_records(self, type=None, name=None, content=None):
        domain = self.domain

        url = '/domains/{0}/records'.format(domain)
        if type:
            url += '/{0}'.format(type)
        if name:
            url += '/{0}'.format(self._relative_name(name))

        raws = self._get(url)

        records = []
        for raw in raws:
            records.append({
                'id': Provider._identifier(raw),
                'type': raw['type'],
                'name': self._full_name(raw['name']),
                'ttl': raw['ttl'],
                'content': raw['data']
            })

        if content:
            records = [
                record for record in records if record['data'] == content]

        LOGGER.debug('list_records: %s', records)

        return records

    def create_record(self, type, name, content):
        domain = self.domain
        relative_name = self._relative_name(name)
        ttl = self._get_lexicon_option('ttl')

        # Retrieve existing data in DNS zone.
        records = self._get('/domains/{0}/records'.format(domain))

        # Check if a record already matches given parameters
        for record in records:
            if (record['type'] == type and self._relative_name(record['name']) == relative_name
                    and record['data'] == content):
                LOGGER.debug(
                    'create_record (ignored, duplicate): %s %s %s', type, name, content)
                return True

        # Append a new entry corresponding to given parameters.
        data = {'type': type, 'name': relative_name, 'data': content}
        if ttl:
            data['ttl'] = ttl

        records.append(data)

        # Synchronize data with inserted record into DNS zone.
        self._put('/domains/{0}/records'.format(domain), records)

        LOGGER.debug('create_record: %s %s %s', type, name, content)

        return True

    def update_record(self, identifier, type=None, name=None, content=None):
        # No identifier is used with GoDaddy.
        # We can rely either:
        #   - only on type/name to get the relevant records, both of them are required
        #     or we will could update to much records ...,
        #   - or by the pseudo-identifier provided
        # Furthermore for type/name approach, we cannot update all matching records, as it
        # would lead o an error (two entries of same type + name cannot have the same content).
        # So for type/name approach, we search first matching record for type/name on which content
        # is different, and we update it before synchronizing the DNS zone.
        if not identifier and not type:
            raise Exception('ERROR: type is required')
        if not identifier and not name:
            raise Exception('ERROR: name is required')

        domain = self.domain
        relative_name = None
        if name:
            relative_name = self._relative_name(name)

        # Retrieve existing data in DNS zone.
        records = self._get('/domains/{0}/records'.format(domain))

        # Get the record to update:
        #   - either explicitly by its identifier,
        #   - or the first matching by its type+name where content does not match
        #     (first match, see first method comment for explanation).
        for record in records:
            if ((identifier and Provider._identifier(record) == identifier) or
                    (not identifier and record['type'] == type
                     and self._relative_name(record['name']) == relative_name
                     and record['data'] != content)):
                record['data'] = content
                break

        # Synchronize data with updated records into DNS zone.
        self._put('/domains/{0}/records'.format(domain), records)

        LOGGER.debug('update_record: %s %s %s', type, name, content)

        return True

    def delete_record(self, identifier=None, type=None, name=None, content=None):
        # For the LOL. GoDaddy does not accept an empty array
        # when updating a particular set of records.
        # It means that you cannot request to remove all records
        # matching a particular type and/or name.
        # Instead, we get ALL records in the DNS zone, update the set,
        # and replace EVERYTHING in the DNS zone.
        # You will always have at minimal NS/SRV entries in the array,
        # otherwise your DNS zone is broken, and updating the zone is the least of your problem ...
        domain = self.domain

        # Retrieve all records in the DNS zone
        records = self._get('/domains/{0}/records'.format(domain))

        relative_name = None
        if name:
            relative_name = self._relative_name(name)

        # Filter out all records which matches the pattern (either identifier
        # or some combination of type/name/content).
        filtered_records = []
        if identifier:
            filtered_records = [
                record for record in records if Provider._identifier(record) != identifier]
        else:
            for record in records:
                if ((not type and not relative_name and not content)
                        or (type and not relative_name and not content and record['type'] != type)
                        or (not type and relative_name and not content
                            and self._relative_name(record['name']) != relative_name)
                        or (not type and not relative_name and content
                            and record['data'] != content)
                        or (type and relative_name and not content
                            and (record['type'] != type
                                 or self._relative_name(record['name']) != relative_name))
                        or (type and not relative_name and content
                            and (record['type'] != type or record['data'] != content))
                        or (not type and relative_name and content
                            and (self._relative_name(record['name']) != relative_name
                                 or record['data'] != content))
                        or (type and relative_name and content
                            and (record['type'] != type
                                 or self._relative_name(record['name']) != relative_name
                                 or record['data'] != content))):
                    filtered_records.append(record)

        # Synchronize data with expurged entries into DNS zone.
        self._put('/domains/{0}/records'.format(domain), filtered_records)

        LOGGER.debug('delete_records: %s %s %s', type, name, content)

        return True

    # GoDaddy provides no identifier for a record, which is a problem
    # where identifiers can be used (delete and update).
    # To circumvent this, we implement a pseudo-identifier,which is basically
    # a hash of type+name+content of a given record.
    # It is far from perfect, as the identifier will change each time
    # we change something in the record ...
    # But at least, one can use 'lexicon godaddy list ...' then
    # 'lexicon godaddy update --identifier ...' to modify specific record.
    # However, 'lexicon godaddy list ...' should be called each time DNS
    # zone had been changed to calculate new identifiers.
    @staticmethod
    def _identifier(record):
        sha256 = hashlib.sha256()
        sha256.update(('type=' + record.get('type', '') + ',').encode('utf-8'))
        sha256.update(('name=' + record.get('name', '') + ',').encode('utf-8'))
        sha256.update(('data=' + record.get('data', '') + ',').encode('utf-8'))
        return sha256.hexdigest()[0:7]

    def _request(self, action='GET', url='/', data=None, query_params=None):
        if not data:
            data = {}
        if not query_params:
            query_params = {}

        # When editing DNS zone, API is unavailable for few seconds
        # (until modifications are propagated).
        # In this case, call to API will return 409 HTTP error.
        # We use the Retry extension to retry the requests until
        # we get a processable reponse (402 HTTP status, or an HTTP error != 409)
        retries = Retry(
            total=10,
            backoff_factor=0.5,
            status_forcelist=[409],
            method_whitelist=frozenset(
                ['GET', 'PUT', 'POST', 'DELETE', 'PATCH'])
        )

        session = requests.Session()
        session.mount('https://', HTTPAdapter(max_retries=retries))

        result = session.request(action, self.api_endpoint + url,
                                 params=query_params,
                                 data=json.dumps(data),
                                 headers={
                                     'Content-Type': 'application/json',
                                     'Accept': 'application/json',
                                     # GoDaddy use a key/secret pair to authenticate
                                     'Authorization': 'sso-key {0}:{1}'.format(
                                         self._get_provider_option(
                                             'auth_key'),
                                         self._get_provider_option('auth_secret'))
                                 })

        result.raise_for_status()

        try:
            # Return the JSON body response if exists.
            return result.json()
        except ValueError:
            # For some requests command (eg. PUT), GoDaddy will not
            # return any JSON, just an HTTP status without body.
            return None
