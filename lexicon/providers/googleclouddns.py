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

def ProviderParser(subparser):
    subparser.description = '''
        The Google Cloud DNS provider requires the JSON file which contains the service account info to connect to the API.
        This service account must own the project role DNS > DNS administrator for the project associated to the DNS zone.
        You can create a new service account and download its info through this url: 
        https://console.cloud.google.com/iam-admin/serviceaccounts?authuser=2'''
    subparser.add_argument('--auth-service-account-info', help='''
        specify the service account info in the Google JSON format: 
        can be either the path of a file prefixed by 'file::' (eg. file::/tmp/service_account_info.json)
        or the base64 encoded content of this file prefixed by 'base64::' (eg. base64::eyJhbGciOyJ...)''')

class Provider(BaseProvider):

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

    def create_record(self, type, name, content):
        if not type or not name or not content:
            raise Exception('Error, type, name and content are mandatory to create a record.')

        identifier = Provider._identifier({'type': type, 'name': name, 'content': content})

        query_params = {
            'type': type,
            'name': self._fqdn_name(name)
        }

        results = self._get('/managedZones/{0}/rrsets'.format(self.domain_id), query_params=query_params)
        
        if not results['rrsets']:
            rrset = {
                'kind': 'dns#resourceRecordSet',
                'name': self._fqdn_name(name),
                'type': type,
                'rrdatas': [ content ]
            }
        else:
            rrset = results['rrsets'][0]
            for rrdata in rrset['rrdatas']:
                if rrdata == content:
                    LOGGER.debug('create_record (ignored, duplicate): %s', identifier)
                    return True

            deletion_action = {
                'deletions': [ rrset ]
            }
            self._post('/managedZones/{0}/changes'.format(self.domain_id), data=deletion_action)
            
            rrset = results['rrsets'][0].copy()
            rrset['rrdatas'].append(content)

        if self.options.get('ttl'):
            rrset['ttl'] = self.options.get('ttl')

        addition_action = {
            'additions': [ rrset ]
        }
        self._post('/managedZones/{0}/changes'.format(self.domain_id), data=addition_action)

        LOGGER.debug('create_record: %s', identifier)

        return True

    @staticmethod
    def _identifier(record):
        digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
        digest.update(('type=' + record.get('type', '') + ',').encode('utf-8'))
        digest.update(('name=' + record.get('name', '') + ',').encode('utf-8'))
        digest.update(('content=' + record.get('content', '') + ',').encode('utf-8'))

        return binascii.hexlify(digest.finalize()).decode('utf-8')[0:7]

    def _request(self, action='GET',  url='/', data=None, query_params=None):
        print(json.dumps(data))
        request = requests.request(action, 
                                   'https://content.googleapis.com/dns/v1/projects/{0}{1}'.format(self._service_account_info['project_id'], url), 
                                   params=None if not query_params else query_params,
                                   data=None if not data else json.dumps(data),
                                   headers={
                                       'Authorization': 'Bearer {0}'.format(self._token),
                                       'Content-type': 'application/json'})
        
        print (request.json())

        request.raise_for_status()
        return request.json()