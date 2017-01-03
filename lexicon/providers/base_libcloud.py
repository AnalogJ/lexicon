from base import Provider as BaseProvider
from libcloud.dns.types import Provider as LibcloudDrivers, RecordType
from libcloud.dns.providers import get_driver
from lexicon.common.exceptions import *

"""Libcloud Provider for Lexicon

Lexicon provides a common interface for querying and managing DNS services
for multiple API's. Historically this was done via custom code for each service,
however when possible we use the libcloud drivers. This module implements the
Lexicon interface and wraps the Libcloud API.

Since we the Libcloud API expects its own internal Record and Zone classes for
passing data around, each method (create_record, update_record, delete_record)
will have a private method (prefixed by `_`) which returns Libcloud classes, and
Lexicon interface methods which return the simple dictionary record structure
that Lexicon expects.

"""

class Provider(BaseProvider):

    def __init__(self, options, provider_options={}):
        super(Provider, self).__init__(options)

    def authenticate(self):
        zones = self.driver.list_zones()
        found_zone = [zone for zone in zones if zone.domain == self.options['domain']]

        if len(found_zone) == 0:
            raise ZoneDoesNotExistError('No zone/domain found', self.provider_name, self.options['domain'])
        if len(found_zone) > 1:
            raise ZoneAmbiguousError('Too many zones/domains found. This should not happen', self.provider_name, self.options['domain'])
        self.zone = found_zone[0]


    # Create record. If record already exists with the same content, do nothing'
    def create_record(self, type, name, content):
        processed_record = self._create_record(type, name, content);
        print 'create_record: {0}'.format(processed_record)
        return processed_record

    def _create_record(self, type, name, content):
        # if self.options.get('ttl'):
        #     data['ttl'] = self.options.get('ttl')
        new_record = self.driver.create_record(self._relative_name(name), self.zone, self._get_type(type), content) #TODO: add support for TTL
        return new_record

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        filtered_records = self._list_records(type, name, content)
        processed_records = map(self._format_record, filtered_records)
        print 'list_records: {0}'.format(processed_records)
        return processed_records

    def _list_records(self, type=None, name=None, content=None):
        return [record for record in self.driver.iterate_records(self.zone) if self._record_match(record, self._get_type(type), name, content)]

    # Create or update a record.
    def update_record(self, identifier, type=None, name=None, content=None):
        processed_record = self._format_record(self._update_record(identifier, type, name, content))
        print 'update_record: {0}'.format(processed_record)
        return processed_record


    def _update_record(self, identifier, type=None, name=None, content=None):
        newly_created = False
        if identifier:
            existing_record = self.driver.get_record(self.zone.id, identifier)
        else:
            records = self._list_records(type, name, content)
            if len(records) == 0 and type and name and content:
                existing_record = self.driver.create_record(self._relative_name(name), self.zone, self._get_type(type), content)
                newly_created = True
            elif len(records) == 0:
                raise RecordDoesNotExistError('Record does not exist. Not enough data to create record.', self.provider_name, self._full_name(name))
            elif len(records) > 1:
                raise RecordAmbiguousError('Too many records found. Could not identify record to update', self.provider_name, self._full_name(name))
            else:
                existing_record = records[0]

        if existing_record and not newly_created:
            existing_record = self.driver.update_record(existing_record,
                                                        self._relative_name(name) if name else existing_record.name,
                                                        self._get_type(type) if type else existing_record.type,
                                                        content if content else existing_record.data)

        return existing_record

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        status = self._delete_record(identifier, type, name, content)
        print 'delete_record: {0}'.format(status)

    def _delete_record(self, identifier=None, type=None, name=None, content=None):
        if identifier:
            existing_record = self.driver.get_record(self.zone.id, identifier)
        else:
            records = self._list_records(type, name, content)
            if len(records) == 0:
                print 'Record does not exist.'
                return True
            elif len(records) > 1:
                raise RecordAmbiguousError('Too many records found. Could not identify record to delete', self.provider_name, self._full_name(name))
            else:
                existing_record = records[0]

        status = self.driver.delete_record(existing_record)
        return status

    def _record_match(self, record, type=None, name=None, content=None):
        matched = True
        if type:
            # print "testing type {0} == {1}".format(record.type, type)
            matched = matched and (record.type == type)
        if name:
            # print "testing name {0} == {1}".format(record.name, self._relative_name(name))
            matched = matched and (record.name == self._relative_name(name))
        if content:
            # print "testing name {0} == {1}".format(record.data, content)
            matched = matched and (record.data == content)

        return matched

    def _format_record(self, record):
        return {
            'type': '{0}'.format(record.type),
            'name': self._full_name(record.name),
            'ttl': record.ttl,
            'content': record.data,
            'id': record.id
        }

    def _get_type(self, type):
        getattr(RecordType, type.upper())