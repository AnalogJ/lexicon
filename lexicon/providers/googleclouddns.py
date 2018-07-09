from __future__ import absolute_import

import json
import logging
import time
import requests
import binascii

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from base64 import urlsafe_b64encode, b64decode

from .base import Provider as BaseProvider

LOGGER = logging.getLogger(__name__)

# Implements the Google Cloud DNS provider.
# This API is quite complicated to use, as it used some unique concepts compared to other providers.
# First of all, it uses a full-fledged OAuth2 authentication, involving signing a JWT and retrieve a Bearer token.
# This hard work is done in the authenticate() process, using the strong and well known "cryptography" package.
# Second, Google Cloud DNS API contains this really particular patterns:
#   - all records of the same type and name are stacked together in a RecordSet representation, 
#       which contains in the rrdatas array all current values for this type/name pair, including
#       explictly monovalued entries like A or CNAME.
#   - modifications can only done through a create/delete pattern: there is no way to update a record
#   - more importantly, this approach extends to all values of a given type/name pair: it means that adding/removing
#       a new value to a TXT entry requires to delete all values of this entry, then recreate it with all 
#       values desired (the old ones plus the new one for adding, the old ones minus the removed one for removing)
# So all the hard work in this provider, appart from the authentication process, is to convert the Lexicon monovalued
#   entries representation to/from the Google multivalued and stacked representation 
#   through create/update/list/delete processes.
def ProviderParser(subparser):
    subparser.description = '''
        The Google Cloud DNS provider requires the JSON file which contains the service account info to connect to the API.
        This service account must own the project role DNS > DNS administrator for the project associated to the DNS zone.
        You can create a new service account, associate a private key, and download its info through this url: 
        https://console.cloud.google.com/iam-admin/serviceaccounts?authuser=2'''
    subparser.add_argument('--auth-service-account-info', help='''
        specify the service account info in the Google JSON format: 
        can be either the path of a file prefixed by 'file::' (eg. file::/tmp/service_account_info.json)
        or the base64 encoded content of this file prefixed by 'base64::' (eg. base64::eyJhbGciOyJ...)''')

class Provider(BaseProvider):

    # We need serveral parameters, which are available in the JSON file provided 
    #   by Google when associating a private key to the relevant service account.
    # So this JSON file is the natural input to configure the provider.
    # It can be provided as a path to the JSON file, or as its content encoded
    #   in base64, which is a suitable portable way in particular for Docker containers.
    # In both cases the content is loaded as bytes, on loaded in a private instance variable.
    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self._token = None

        if self.options['auth_service_account_info'].startswith('file::'):
            with open(self.options['auth_service_account_info'].replace('file::', ''), 'rb') as file:
                service_account_info_bytes = file.read()
        elif self.options['auth_service_account_info'].startswith('base64::'):
            service_account_info_bytes = b64decode(self.options['auth_service_account_info'].replace('base64::', ''))
        else:
            raise Exception('Invalid value passed to --auth-service-account-info, should be a path prefixed with \'file::\' or a base64 value prefixed by \'base64::\'.')

        self._service_account_info = json.loads(service_account_info_bytes.decode('utf-8'))

        if not self._service_account_info['client_email'] or not self._service_account_info['private_key'] or not self._service_account_info['project_id']:
            raise Exception('Invalid service account info (missing either client_email/private_key/project_id key).')
    
    # We have a real authentication here, which uses the OAuth protocol:
    #   - a JWT token is forged with the Google Cloud DNS access claims, using the service account info loaded by the constructor,
    #   - this JWT token is signed by a PKCS1v15 signature using the RSA private key associated to the service account,
    #   - this JWT token is then submitted to the Google API, which returns an access token
    #   - this access token will be used for every future HTTP request to the Google Cloud DNS API to authenticate the user.
    #   - finally we make a first authenticated request to retrieve the managed zone id, which will also be used on future requests.
    # This access token has a default lifetime of 10 minutes, but is used only for the current Lexicon operation, so it should be sufficient.
    def authenticate(self):
        jwt_header = {
            'alg': 'RS256',
            'typ': 'JWT'
        }
        jwt_header_bytes = urlsafe_b64encode(json.dumps(jwt_header).encode('utf-8'))
        
        epoch_time = int(time.time())
        jwt_claims_set = {
            'iss': self._service_account_info['client_email'],
            'scope': 'https://www.googleapis.com/auth/ndev.clouddns.readwrite',
            'aud': 'https://www.googleapis.com/oauth2/v4/token',
            'exp': epoch_time + 60 * 10,
            'iat': epoch_time
        }
        jwt_claims_set_bytes = urlsafe_b64encode(json.dumps(jwt_claims_set).encode('utf-8'))

        private_key = serialization.load_pem_private_key(
            self._service_account_info['private_key'].encode('utf-8'),
            password=None,
            backend=default_backend()
        )

        jwt_sign = private_key.sign(
            b'.'.join([jwt_header_bytes, jwt_claims_set_bytes]),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        jwt_sign_bytes = urlsafe_b64encode(jwt_sign)

        jwt_bytes = b'.'.join([jwt_header_bytes, jwt_claims_set_bytes, jwt_sign_bytes])

        post_data = {
            'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion': jwt_bytes
        }
        post_header = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        auth_request = requests.request('POST', 'https://www.googleapis.com/oauth2/v4/token', data=post_data, headers=post_header)

        auth_request.raise_for_status()
        post_result = auth_request.json()

        if not post_result['access_token']:
            raise Exception('Error, could not grant RW access on the Google Cloud DNS API for user: {0}'.format(self.options['auth_email']))

        self._token = post_result['access_token']

        results = self._get('/managedZones')

        targetedManagedZoneIds = [managedZone['id'] for managedZone in results['managedZones'] if managedZone['dnsName'] == '{0}.'.format(self.options['domain'])]

        if not targetedManagedZoneIds:
            raise Exception('Error, domain {0} is not registered for this project'.format(self.options['domain']))

        self.domain_id = targetedManagedZoneIds[0]

    # List all records for the given type/name/content.
    # It is quite straight forward to request data, the biggest operation is to convert
    #   the stacked multivalued RecordSets into Lexicon monovalued entries.
    # Plese not that we could provide type and name to the API to make the filtering, 
    #   but providing the type makes the name mandatory with the Google Cloud DNS API, and
    #   name is not always available (we can ask for every TXT record for example). So to stick to
    #   the most general case, its preferable to always get all records and be free to filter
    #   the way we want afterwards.
    def list_records(self, type=None, name=None, content=None):
        results = self._get('/managedZones/{0}/rrsets'.format(self.domain_id))

        records = []

        for rrset in results['rrsets']:
            for rrdata in rrset['rrdatas']:
                record = {
                    'type': rrset['type'],
                    'name': self._full_name(rrset['name']),
                    'ttl': rrset['ttl'],
                    'content': rrdata
                }
                self._clean_TXT_record(record)
                record['id'] = Provider._identifier(record)
                records.append(record)

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            records = [record for record in records if record['name'] == self._full_name(name)]
        if content:
            records = [record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)

        return records

    # Create the record with provided type, name and content.
    # Because of the way this API is constructed, it is quite complex in fact.
    # Indeed we need to know if there is already a RecordSet for the type/name pair, and update
    #   or create accordingly the RecordSet. Furthermore, we need first to delete the old RecordSet
    #   if it exists, to replace it with the RecordSet containing the new content we want.
    def create_record(self, type, name, content):
        if not type or not name or not content:
            raise Exception('Error, type, name and content are mandatory to create a record.')

        identifier = Provider._identifier({'type': type, 'name': self._full_name(name), 'content': content})

        query_params = {
            'type': type,
            'name': self._fqdn_name(name)
        }

        results = self._get('/managedZones/{0}/rrsets'.format(self.domain_id), query_params=query_params)

        rrdatas = []
        changes = {}
        if results['rrsets']:
            rrset = results['rrsets'][0]
            for rrdata in rrset['rrdatas']:
                if rrdata == Provider._normalize_content(rrset['type'], content):
                    LOGGER.debug('create_record (ignored, duplicate): %s', identifier)
                    return True

            changes['deletions'] = [{
                'name': rrset['name'],
                'type': rrset['type'],
                'ttl': rrset['ttl'],
                'rrdatas': rrset['rrdatas'][:]
            }]

            rrdatas = rrset['rrdatas'][:]
        
        rrdatas.append(Provider._normalize_content(type, content))

        changes['additions'] = [{
            'name': self._fqdn_name(name),
            'type': type,
            'ttl': self.options.get('ttl'),
            'rrdatas': rrdatas
        }]

        self._post('/managedZones/{0}/changes'.format(self.domain_id), data=changes)

        LOGGER.debug('create_record: %s', identifier)

        return True

    # Update a record for the given identifier or type/name pair with the given content if provided.
    # Again because of the API specification, updating is even more complex than creating, as we need
    #   to take into account every RecordSet that should be destroyed then recreated.
    # As all the hard work has been done on list_record, create_record and delete_record, we use a
    #   combination of these three methods to obtain the state we want.
    # Even if this make the operation very costly regarding the number of requests to do, it allows
    #   the implementation to be way more readable (without that, it would take grossly the size of 
    #   the three quoted methods).
    def update_record(self, identifier, type=None, name=None, content=None):
        if not identifier and (not type or not name):
            raise Exception('Error, identifier or type+name parameters are required.')

        if identifier:
            records = self.list_records()
            records_to_update = [record for record in records if record['id'] == identifier]
        else:
            records_to_update = self.list_records(type=type, name=name)

        if not records_to_update:
            raise Exception('Error, could not find a record for given identifier: {0}'.format(identifier))

        if len(records_to_update) > 1:
            LOGGER.warn('Warning, multiple records found for given parameters, only first one will be updated: %s', records_to_update)

        record_identifier = records_to_update[0]['id']

        original_level = LOGGER.getEffectiveLevel()
        LOGGER.setLevel(logging.WARNING)
        self.delete_record(record_identifier)

        new_record = {
            'type': type if type else records_to_update[0]['type'], 
            'name': name if name else records_to_update[0]['name'], 
            'content': content if content else records_to_update[0]['content']
        }

        self.create_record(new_record['type'], new_record['name'], new_record['content'])
        LOGGER.setLevel(original_level)

        LOGGER.debug('update_record: %s => %s', record_identifier, Provider._identifier(new_record))

        return True

    # Delete a record for the given identifier or the given type/name/content.
    # Really complex to do, because a lot of RecordSets can be updated (so destroyed and recreated)
    #   depending on the given condition (eg. with content alone, every record could be inspected).
    # There is mainly to cases:
    #   - either an association of one or more between type, name and content is given
    #   - either an identifier is given, and we extract the type + name + content to process as the first case.
    # Anyway, we will need to parse every RecordSet available, and for each of them which match the conditions:
    #   - mark as deletion the existing RecordSet
    #   - remove the targeted content from the RecordSet
    #   - mark as addition the update RecordSet with the subset of rrdatas if rrdatas is not empty
    #   - do not mark as additions RecordSets whose rrdatas subset become empty: 
    #       for this type/name pair, all RecordSet needs to go away.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        results = self._get('/managedZones/{0}/rrsets'.format(self.domain_id))

        if identifier:
            changes = self._process_records_to_delete_by_identifier(results, identifier)
        else:
            changes = self._process_records_to_delete_by_parameters(results, type, name, content)

        if not changes:
            raise Exception('Could not find existing record matching the given parameters.')

        self._post('/managedZones/{0}/changes'.format(self.domain_id), data=changes)

        LOGGER.debug('delete_records: %s %s %s %s', identifier, type, name, content)

        return True

    # Calculate the changes to do based on the record to remove identified by its identifier.
    # This implementation find the corresponding record, and use its type + name + value to
    #   delegate the processing to _process_records_to_delete_by_parameters.
    def _process_records_to_delete_by_identifier(self, results, identifier):
        for rrset in results['rrsets']:
            for rrdata in rrset['rrdatas']:
                record = {
                    'type': rrset['type'], 
                    'name': self._full_name(rrset['name']), 
                    'content': rrdata
                }

                self._clean_TXT_record(record)
                record_identifier = Provider._identifier(record)

                if identifier == record_identifier:
                    return self._process_records_to_delete_by_parameters(results, record['type'], record['name'], record['content'])

        return None

    # Calculate the changes to do based on the records to remove identified by type/name/content.
    # Additions and deletions are registered accordingly in the changes, and RecordSet with empty
    #   rrdatas after its subset are not marked in additions to be completly removed from the DNS zone.
    def _process_records_to_delete_by_parameters(self, results, type=None, name=None, content=None):
        rrsets_to_modify = results['rrsets']

        if type:
            rrsets_to_modify = [rrset for rrset in rrsets_to_modify if rrset['type'] == type]
        if name:
            rrsets_to_modify = [rrset for rrset in rrsets_to_modify if rrset['name'] == self._fqdn_name(name)]
        if content:
            rrsets_to_modify = [rrset for rrset in rrsets_to_modify if ('"{0}"'.format(content) if rrset['type'] == 'TXT' else content) in rrset['rrdatas']]

        changes = {
            'additions': [], 
            'deletions': []
        }

        for rrset_to_modify in rrsets_to_modify:
            changes['deletions'].append({
                'name': rrset_to_modify['name'],
                'type': rrset_to_modify['type'],
                'ttl': rrset_to_modify['ttl'],
                'rrdatas': rrset_to_modify['rrdatas'][:]
            })

            if content:
                new_rrdatas = rrset_to_modify['rrdatas'][:]
                new_rrdatas.remove('"{0}"'.format(content) if rrset_to_modify['type'] == 'TXT' else content)
                if new_rrdatas:
                    changes['additions'].append({
                        'name': rrset_to_modify['name'],
                        'type': rrset_to_modify['type'],
                        'ttl': rrset_to_modify['ttl'],
                        'rrdatas': new_rrdatas
                    })

        if not changes['additions'] and not changes['deletions']:
            return None

        return changes

    # With Google Cloud DNS API, content of CNAME entries must be FQDN (with a trailing dot),
    #   and content of TXT entries must be quoted. This static method ensures that.
    @staticmethod
    def _normalize_content(type, content):
        if type == 'TXT':
            return '"{0}"'.format(content)
        if type == 'CNAME':
            return '{0}.'.format(content) if not content.endswith('.') else content
        
        return content

    # Google Cloud DNS API does not provide identifier for RecordSets.
    # So we need to calculate our own identifier at runtime.
    # It is based on a SHA256 hash with the most relevant parameters of a record: type, name and content.
    # Note that the identifier is calculated on a Lexicon monovalued entry, not a Google stacked multivalued RecordSet,
    #   to make it usable during Lexicon calls to updates and deletions.
    @staticmethod
    def _identifier(record):
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(('type=' + record.get('type', '') + ',').encode('utf-8'))
        digest.update(('name=' + record.get('name', '') + ',').encode('utf-8'))
        digest.update(('content=' + record.get('content', '') + ',').encode('utf-8'))

        return binascii.hexlify(digest.finalize()).decode('utf-8')[0:7]

    # The request, when authenticated, is really standard:
    #   the request body is encoded as application/json for POST (so the use of 'json' config instead of 'data' in request),
    #   the body response is also encoded as application/json for GET and POST,
    #   and the request headers must contain the access token in the 'Authorization' field.
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        request = requests.request(action, 
                                   'https://content.googleapis.com/dns/v1/projects/{0}{1}'.format(self._service_account_info['project_id'], url), 
                                   params=None if not query_params else query_params,
                                   json=None if not data else data,
                                   headers={'Authorization': 'Bearer {0}'.format(self._token)})

        request.raise_for_status()
        return request.json()