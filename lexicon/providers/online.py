"""Module provider for Online.net"""
from __future__ import absolute_import
import json
import logging

import requests
from lexicon.providers.base import Provider as BaseProvider


LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['online.net']


def provider_parser(subparser):
    """Configure provider parser for Online.net"""
    subparser.add_argument("--auth-token", help="specify private api token")


def _to_data(rtype, content):
    if rtype == "TXT":
        return '"{0}"'.format(content)
    return content


class Provider(BaseProvider):
    """Provider class for Online.net"""
    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.zone_name = 'Zone Automatic Lexicon '
        self.passive_zone = None
        self.active_zone = None
        self.domain_id = self.domain
        self.api_endpoint = 'https://api.online.net/api/v1'

    def _authenticate(self):
        self._init_zones()

    def _list_zones(self):
        return self._get('/domain/{0}/version'.format(self.domain_id))

    def _init_zones(self):
        # sets current zone version
        zone_name_a = self.zone_name + 'A'
        zone_name_b = self.zone_name + 'B'
        active_row = None
        passive_row = None
        for row in self._list_zones():
            if row['active']:
                active_row = row
            elif row['name'] == zone_name_a or row['name'] == zone_name_b:
                passive_row = row

        if passive_row is None:
            passive_row = self._post('/domain/{0}/version'.format(self.domain_id), {
                'name': zone_name_b if active_row['name'] == zone_name_a else zone_name_a
            })

        self.active_zone = active_row['uuid_ref']
        self.passive_zone = passive_row['uuid_ref']
        self._update_passive_zone()

    def _update_passive_zone(self):
        self._put(
            '/domain/{0}/version/{1}/zone_from_bind'.format(
                self.domain_id,
                self.passive_zone
            ),
            self._get_bind_zone()
        )

    def _get_bind_zone(self):
        records = self._list_zone_records(self.active_zone)
        # then convert records to bind format
        bind_str = ''
        for record in records:
            bind_str = bind_str + '{0} {1} IN {2} {3}{4}\n'.format(
                record['name'] or '@',
                record['ttl'],
                record['type'],
                '{0} '.format(record['aux']) if 'aux' in record else '',
                record['data'] or ''
            )
        return bind_str

    def _enable_zone(self):
        zone = self.passive_zone
        if zone is None:
            raise Exception("Could not enable uninitialized passive_zone")
        self._patch('/domain/{0}/version/{1}/enable'.format(
            self.domain_id,
            zone
        ))
        self.passive_zone = self.active_zone
        self.active_zone = zone
        self._update_passive_zone()

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype, name, content):
        try:
            record = self._find_record(rtype, name, content)
            if record is not None:
                return True

            record = {
                'name': self._fqdn_name(name),
                'type': rtype,
                'data': _to_data(rtype, content),
                'priority': self._get_lexicon_option('priority') or '',
                'ttl': self._get_lexicon_option('ttl') or ''
            }

            self._post(
                '/domain/{0}/version/{1}/zone'.format(
                    self.domain_id,
                    self.passive_zone
                ),
                record
            )
        except BaseException as error:
            LOGGER.debug(error)
            return False

        self._enable_zone()
        LOGGER.debug('create_record: %s', True)
        return True

    def _find_zone_records(self, zone, rtype=None, name=None, content=None):
        records = []
        for record in self._list_zone_records(zone):
            processed_record = {
                'id': record['id'],
                'type': record['type'],
                'name': self._full_name(record['name']),
                'ttl': record['ttl'],
                'content': record['data'],
                'priority': record['aux'] if 'aux' in record else ''
            }
            records.append(self._clean_TXT_record(processed_record))

        if rtype:
            records = [record for record in records if record['type'] == rtype]
        if name:
            full_name = self._full_name(name)
            records = [
                record for record in records if record['name'] == full_name]
        if content:
            records = [
                record for record in records if record['content'] == content]

        LOGGER.debug('list_records: %s', records)
        return records

    def _list_zone_records(self, zone_id):
        return self._get('/domain/{0}/version/{1}/zone'.format(self.domain_id, zone_id))

    def _list_records(self, rtype=None, name=None, content=None):
        return self._find_zone_records(self.passive_zone, rtype, name, content)

    def _find_record(self, rtype=None, name=None, content=None):
        records = self._list_records(rtype, name, content)
        if not records:
            return None
        return records[0]

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        record = self._find_record(rtype, name)
        if record is None:
            LOGGER.debug("cannot find record to update: %s %s %s",
                         identifier, rtype, name)
            return True
        if rtype:
            record['type'] = rtype
        if name:
            record['name'] = self._fqdn_name(name)
        if content:
            record['data'] = _to_data(rtype, content)
        if self._get_lexicon_option('ttl'):
            record['ttl'] = self._get_lexicon_option('ttl')
        # it is weird that 'aux' becomes 'priority' in online's api
        if self._get_lexicon_option('priority'):
            record['priority'] = self._get_lexicon_option('priority')

        if identifier is None:
            identifier = record['id']

        record.pop('id')

        try:
            self._patch('/domain/{0}/version/{1}/zone/{2}'.format(
                self.domain_id,
                self.passive_zone,
                identifier
            ), record)

        except BaseException as error:
            LOGGER.debug(error)
            return False

        self._enable_zone()
        # If it didn't raise from the http status code, then we're good
        LOGGER.debug('update_record: %s', identifier)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        records = self._list_records(rtype, name, content)
        if not records:
            LOGGER.debug("Cannot find records %s %s %s", rtype, name, content)
            return False
        LOGGER.debug('delete_records: %s records found', len(records))
        try:
            for record in records:
                self._delete('/domain/{0}/version/{1}/zone/{2}'.format(
                    self.domain_id,
                    self.passive_zone,
                    record['id']
                ))
        except BaseException as error:
            LOGGER.debug(error)
            return False

        self._enable_zone()
        # is always True at this point, if a non 200 response is returned an error is raised.
        LOGGER.debug('delete_record: %s', True)
        return True

    def _patch(self, url='/', data=None, query_params=None):
        return self._request('PATCH', url, data=data, query_params=query_params)

    # Helpers
    def _request(self, action='GET', url='/', data=None, query_params=None):
        if query_params is None:
            query_params = {}

        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer {0}'.format(self._get_provider_option('auth_token'))
        }
        if data is not None:
            if isinstance(data, str):
                headers['Content-Type'] = 'text/plain'
            else:
                headers['Content-Type'] = 'application/json'
                data = json.dumps(data)

        response = requests.request(
            action,
            self.api_endpoint + url,
            params=query_params,
            data=data,
            headers=headers
        )
        # if the request fails for any reason, throw an error.
        response.raise_for_status()

        return response.json() if response.text else ''
