from __future__ import absolute_import
from __future__ import print_function

import json
import logging

import requests

from .base import Provider as BaseProvider

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    subparser.add_argument("--auth-token", help="specify private api token")

def to_data(type, content):
    if type == "TXT":
        return '"{0}"'.format(content)
    else:
        return content

class Provider(BaseProvider):

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options, engine_overrides)
        self.zone_name = 'Zone Automatic Lexicon '
        self.passive_zone = None
        self.active_zone = None
        self.domain_id = self.options['domain']
        self.api_endpoint = self.engine_overrides.get('api_endpoint', 'https://api.online.net/api/v1')

    def authenticate(self):
        self.init_zones()

    def list_zones(self):
        return self._get('/domain/{0}/version'.format(self.domain_id))

    def init_zones(self):
        # sets current zone version
        zone_name_a = self.zone_name + 'A'
        zone_name_b = self.zone_name + 'B'
        active_row = None
        passive_row = None
        for row in self.list_zones():
            if row['active'] == True:
                active_row = row
            elif row['name'] == zone_name_a or row['name'] == zone_name_b:
                passive_row = row

        if passive_row is None:
            passive_row = self._post('/domain/{0}/version'.format(self.domain_id), {
                'name': zone_name_b if active_row['name'] == zone_name_a else zone_name_a
            })

        self.active_zone = active_row['uuid_ref']
        self.passive_zone = passive_row['uuid_ref']
        self.update_passive_zone()


    def update_passive_zone(self):
        self._put(
            '/domain/{0}/version/{1}/zone_from_bind'.format(
                self.domain_id,
                self.passive_zone
            ),
            self.get_bind_zone()
        )

    def get_bind_zone(self):
        records = self.list_zone_records(self.active_zone)
         # then convert records to bind format
        bindStr = ''
        for record in records:
            bindStr = bindStr + '{0} {1} IN {2} {3}{4}\n'.format(
                record['name'] or '@',
                record['ttl'],
                record['type'],
                '{0} '.format(record['aux']) if 'aux' in record else '',
                record['data'] or ''
            )
        return bindStr

    def enable_zone(self):
        zone = self.passive_zone
        if zone is None:
            raise Exception("Could not enable uninitialized passive_zone")
        payload = self._patch('/domain/{0}/version/{1}/enable'.format(
            self.domain_id,
            zone
        ))
        self.passive_zone = self.active_zone
        self.active_zone = zone
        self.update_passive_zone()


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        try:
            record = self.find_record(type, name, content)
            if record is not None:
                return True

            record = {
                'name': self._fqdn_name(name),
                'type': type,
                'data': to_data(type, content),
                'priority': self.options['priority'] or '',
                'ttl': self.options['ttl'] or ''
            }

            payload = self._post(
                '/domain/{0}/version/{1}/zone'.format(
                    self.domain_id,
                    self.passive_zone
                ),
                record
            )
        except Exception as e:
            logger.debug(e)
            return False

        self.enable_zone()
        logger.debug('create_record: %s', True)
        return True

    def find_zone_records(self, zone, type=None, name=None, content=None):
        records = []
        for record in self.list_zone_records(zone):
            processed_record = {
                'id': record['id'],
                'type': record['type'],
                'name': self._full_name(record['name']),
                'ttl': record['ttl'],
                'content': record['data'],
                'priority': record['aux'] if 'aux' in record else ''
            }
            records.append(self._clean_TXT_record(processed_record))

        if type:
            records = [record for record in records if record['type'] == type]
        if name:
            fullName = self._full_name(name)
            records = [record for record in records if record['name'] == fullName]
        if content:
            records = [record for record in records if record['content'] == content]

        logger.debug('list_records: %s', records)
        return records

    def list_zone_records(self, zone_id):
        return self._get('/domain/{0}/version/{1}/zone'.format(self.domain_id, zone_id))

    def list_records(self, type=None, name=None, content=None):
        return self.find_zone_records(self.passive_zone, type, name, content)

    def find_record(self, type=None, name=None, content=None):
        record = None
        records = self.list_records(type, name, content)
        if len(records) < 1:
            return None
        else:
            return records[0]


    # Create or update a record.
    def update_record(self, id, type=None, name=None, content=None):
        record = self.find_record(type, name)
        if record is None:
            logger.debug("cannot find record to update: %s %s %s", id, type, name)
            return True
        if type:
            record['type'] = type
        if name:
            record['name'] = self._fqdn_name(name)
        if content:
            record['data'] = to_data(type, content)
        if self.options.get('ttl'):
            record['ttl'] = self.options.get('ttl')
        # it is weird that 'aux' becomes 'priority' in online's api
        if self.options['priority']:
            record['priority'] = self.options['priority']

        if id is None:
            id = record['id']

        record.pop('id')

        try:
            payload = self._patch('/domain/{0}/version/{1}/zone/{2}'.format(
                self.domain_id,
                self.passive_zone,
                id
            ), record)

        except Exception as e:
            logger.debug(e)
            return False

        self.enable_zone()
        # If it didn't raise from the http status code, then we're good
        logger.debug('update_record: %s', id)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, id=None, type=None, name=None, content=None):
        records = self.list_records(type, name, content)
        if len(records) == 0:
            logger.debug("Cannot find records %s %s %s", type, name, content)
            return False
        logger.debug('delete_records: %s records found', len(records))
        try:
            for record in records:
                payload = self._delete('/domain/{0}/version/{1}/zone/{2}'.format(
                    self.domain_id,
                    self.passive_zone,
                    record['id']
                ))
        except Exception as e:
            logger.debug(e)
            return False

        self.enable_zone()
        # is always True at this point, if a non 200 response is returned an error is raised.
        logger.debug('delete_record: %s', True)
        return True

    def _patch(self, url='/', data=None, query_params=None):
        return self._request('PATCH', url, data=data, query_params=query_params)

    # Helpers
    def _request(self, action='GET',  url='/', data=None, query_params=None):
        if query_params is None:
            query_params = {}

        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer {0}'.format(self.options['auth_token'])
        }
        if data is not None:
            if type(data) is str:
                headers['Content-Type'] = 'text/plain';
            else:
                headers['Content-Type'] = 'application/json';
                data = json.dumps(data)

        r = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=data,
            headers=headers
        )
        r.raise_for_status()  # if the request fails for any reason, throw an error.

        return r.text and r.json() or ''
