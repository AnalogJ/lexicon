from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify token used authenticate to DNS provider")

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.domain_id = None
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.nsone.net/v1')

    def authenticate(self):

        payload = self._get('/zones/{0}'.format(self.options['domain']))

        if not payload['id']:
            raise Exception('No domain found')

        self.domain_id = self.options['domain']


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        record = {
            'type': type,
            'domain': self._full_name(name),
            'zone': self.domain_id,
            'answers':[
                {"answer": [content]}
            ]
        }
        payload = {}
        try:
            payload = self._put('/zones/{0}/{1}/{2}'.format(self.domain_id, self._full_name(name),type), record)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 400:
                payload = {}

                # http 400 is ok here, because the record probably already exists
        logger.debug('create_record: %s', 'id' in payload)
        return 'id' in payload

    def _find_record(self, domain, _type=None):
        """search for a record on NS1 across zones. returns None if not found."""

        def _is_matching(record):
            """filter function for records"""

            if domain and record.get('domain', None) != domain:
                return False
            if _type and record.get('type', None) != _type:
                return False
            return True

        payload = self._get('/search?q={0}&type=record'.format(domain))
        for record in payload:
            if _is_matching(record):
                match = record
                break
        else:
            # no such domain on ns1
            return None

        record = self._get('/zones/{0}/{1}/{2}'.format(match['zone'], match['domain'], match['type']))
        if record.get('message', None):
            return None # {"message":"record not found"}
        short_answers = [ x['answer'][0] for x in record['answers'] ]

        # ensure a compatibility level with self.list_records
        record['short_answers'] = short_answers
        return record

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):

        def _resolve_link(record, recurse=0):
            # https://ns1.com/articles/cname-alias-and-linked-records
            # - recursion is allowed
            # - link source and link target are always of the same type
            # - target can be anywhere on ns1, not necessarily self.domain_id.
            if record.get('link', None) is None:
                # not a linked record
                return record

            if recurse < 1:
                return None

            match = self._find_record(record['link'], _type=record['type'])
            if not match:
                return None

            return _resolve_link(match, recurse=recurse-1)

        payload = self._get('/zones/{0}'.format(self.domain_id))
        records = []
        for record in payload['records']:

            if type and record['type'] != type:
                continue

            if name and record['domain'] != self._full_name(name):
                continue

            link_target = _resolve_link(record, recurse=3)

            if link_target and link_target.get('short_answers', None):
                # target found (could be the same as orig record)
                answer = link_target['short_answers'][0]
            else:
                # recursion limit reached. or unhandled record format.
                answer = ''

            if content and answer != content:
                continue

            processed_record = {
                'type': record['type'],
                'name': record['domain'],
                'ttl': record['ttl'],
                'content': answer,
                #this id is useless unless your doing record linking. Lets return the original record identifier.
                'id': '{0}/{1}/{2}'.format(self.domain_id, record['domain'], record['type'])
            }
            records.append(processed_record)

        logger.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):

        data = {}
        payload = None
        new_identifier = "{0}/{1}/{2}".format(self.domain_id, self._full_name(name),type)

        if(new_identifier == identifier or (type is None and name is None)):
            # the identifier hasnt changed, or type and name are both unspecified, only update the content.
            data['answers'] = [
                {"answer": [content]}
            ]
            self._post('/zones/{0}'.format(identifier), data)

        else:
            # identifiers are different
            # get the old record, create a new one with updated data, delete the old record.
            old_record = self._get('/zones/{0}'.format(identifier))
            self.create_record(type or old_record['type'], name or old_record['domain'], content or old_record['answers'][0]['answer'][0])
            self.delete_record(identifier)

        logger.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        if not identifier:
            records = self.list_records(type, name, content)
            logger.debug('records: %s', records)
            if len(records) == 1:
                identifier = records[0]['id']
            else:
                raise Exception('Record identifier could not be found.')
        payload = self._delete('/zones/{0}'.format(identifier))

        # is always True at this point, if a non 200 response is returned an error is raised.
        logger.debug('delete_record: %s', True)
        return True


    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if data is None:
            data = {}
        if query_params is None:
            query_params = {}
        default_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-NSONE-Key': self.options['auth_token']
        }
        default_auth = None

        r = requests.request(action, self.api_endpoint + url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers,
                             auth=default_auth)
        r.raise_for_status()  # if the request fails for any reason, throw an error.
        return r.json()
