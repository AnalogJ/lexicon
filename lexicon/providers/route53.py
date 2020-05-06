"""Provide support to Lexicon for AWS Route 53 DNS changes."""
from __future__ import absolute_import
import hashlib
import logging
import re

from lexicon.providers.base import Provider as BaseProvider


try:
    import boto3  # optional dep
    import botocore  # optional dep
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = [re.compile(r'^awsdns-\d+\.\w+$')]


def provider_parser(subparser):
    """Specify arguments for AWS Route 53 Lexicon Provider."""
    subparser.add_argument("--auth-access-key",
                           help="specify ACCESS_KEY for authentication")
    subparser.add_argument("--auth-access-secret",
                           help="specify ACCESS_SECRET for authentication")
    subparser.add_argument(
        "--private-zone",
        help=("indicates what kind of hosted zone to use. If true, use "
              "only private zones. If false, use only public zones"))

    # TODO: these are only required for testing, we should figure out
    # a way to remove them & update the integration tests
    # to dynamically populate the auth credentials that are required.
    subparser.add_argument(
        "--auth-username", help="alternative way to specify the ACCESS_KEY for authentication")
    subparser.add_argument(
        "--auth-token", help="alternative way to specify the ACCESS_SECRET for authentication")


class RecordSetPaginator(object):  # pylint: disable=useless-object-inheritance
    """Paginate through complete list of record sets."""

    def __init__(self, r53_client, hosted_zone_id, max_items=None):
        """Initialize paginator."""
        self.r53_client = r53_client
        self.hosted_zone_id = hosted_zone_id
        self.max_items = max_items

    def get_record_sets(self, **kwargs):
        """Retrieve a page from API."""
        return self.r53_client.list_resource_record_sets(**kwargs)

    def get_base_kwargs(self):
        """Get base kwargs for API call."""
        kwargs = {
            'HostedZoneId': self.hosted_zone_id
        }
        if self.max_items is not None:
            kwargs.update({
                'MaxItems': str(self.max_items)
            })
        return kwargs

    def all_record_sets(self):
        """Generator to loop through current record set.

        Call next page if it exists.
        """
        is_truncated = True
        start_record_name = None
        start_record_type = None
        kwargs = self.get_base_kwargs()
        while is_truncated:
            if start_record_name is not None:
                kwargs.update({
                    'StartRecordName': start_record_name,
                    'StartRecordType': start_record_type
                })
            result = self.get_record_sets(**kwargs)
            for record_set in result.get('ResourceRecordSets', []):
                yield record_set

            is_truncated = result.get('IsTruncated', False)

            start_record_name = result.get('NextRecordName', None)
            start_record_type = result.get('NextRecordType', None)


class Provider(BaseProvider):
    """Provide AWS Route 53 implementation of Lexicon Provider interface."""

    def __init__(self, config):
        """Initialize AWS Route 53 DNS provider."""
        super(Provider, self).__init__(config)
        self.domain_id = None
        self.private_zone = self._get_provider_option('private_zone')
        # instantiate the client
        self.r53_client = boto3.client(
            'route53',
            aws_access_key_id=self._get_provider_option(
                'auth_access_key') or self._get_provider_option('auth_username'),
            aws_secret_access_key=self._get_provider_option(
                'auth_access_secret') or self._get_provider_option('auth_token')
        )

    def filter_zone(self, data):
        """Check if a zone is private"""
        if self.private_zone is not None:
            if data['Config']['PrivateZone'] != self.str2bool(self.private_zone):
                return False

        if data['Name'] != '{0}.'.format(self.domain):
            return False

        return True

    @staticmethod
    def str2bool(input_string):
        """Convert a string to boolean"""
        return input_string.lower() in ('true', 'yes')

    def _authenticate(self):
        """Determine the hosted zone id for the domain."""
        try:
            hosted_zones = self.r53_client.list_hosted_zones_by_name()[
                'HostedZones'
            ]
            hosted_zone = next(
                hz for hz in hosted_zones
                if self.filter_zone(hz)
            )
            self.domain_id = hosted_zone['Id']
        except StopIteration:
            raise Exception('No domain found')

    def _change_record_sets(self, action, rtype, name, content):
        ttl = self._get_lexicon_option('ttl')
        resource_records = []
        if isinstance(content, list):
            for i in content:
                value = '"{0}"'.format(i) if rtype in ['TXT', 'SPF'] else i
                resource_records.append({'Value': value})
        else:
            value = '"{0}"'.format(content) if rtype in ['TXT', 'SPF'] else content
            resource_records.append({'Value': value})
        try:
            self.r53_client.change_resource_record_sets(
                HostedZoneId=self.domain_id,
                ChangeBatch={
                    'Comment': '{0} using lexicon Route 53 provider'.format(
                        action
                    ),
                    'Changes': [
                        {
                            'Action': action,
                            'ResourceRecordSet': {
                                'Name': self._fqdn_name(name),
                                'Type': rtype,
                                'TTL': ttl if ttl is not None else 300,
                                'ResourceRecords': resource_records
                            }
                        }
                    ]
                }
            )
            return True
        except botocore.exceptions.ClientError as error:
            if "Duplicate Resource Record" in error.response['Error']['Message']:
                # Duplicate resource, that have been a noop. This is expected.
                return True
            LOGGER.error(str(error), exc_info=True)
            return False

    def _create_record(self, rtype, name, content):
        """Create a record in the hosted zone."""
        existing_records = self._list_record_sets(rtype, name)
        if existing_records:
            existing_record = existing_records[0]
            if isinstance(existing_records[0]['content'], list):
                return self._change_record_sets(
                    'UPSERT', existing_record['type'], existing_record['name'],
                    existing_record['content'] + [content])
            return self._change_record_sets(
                'UPSERT', rtype, name, [existing_record['content']] + [content])
        return self._change_record_sets('CREATE', rtype, name, content)

    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        """Update a record from the hosted zone."""
        if identifier:
            records = [record for record in self._list_records()
                       if identifier == _identifier(record)]
            if not records:
                raise ValueError('No record found for identifier {0}'.format(identifier))
            record = records[0]
            rtype = record['type']
            name = record['name']

        existing_records = self._list_record_sets(rtype, name)
        if not existing_records:
            raise ValueError('No matching record to update was found.')

        for existing_record in existing_records:
            if isinstance(existing_record['content'], list):
                # Multiple values in record.
                LOGGER.warning(
                    'Warning, multiple records found for given parameters, '
                    'only first entry will be updated: %s', existing_record)
                new_content = existing_record['content'].copy()
                new_content[0] = content
            else:
                new_content = content

            self._change_record_sets('UPSERT', existing_record['type'],
                                     existing_record['name'], new_content)

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """Delete a record from the hosted zone."""
        if identifier:
            matching_records = [record for record in self._list_records()
                                if identifier == _identifier(record)]
            if not matching_records:
                raise ValueError('No record found for identifier {0}'.format(identifier))
            rtype = matching_records[0]['type']
            name = matching_records[0]['name']
            content = matching_records[0]['content']

        existing_records = self._list_record_sets(rtype, name, content)
        if not existing_records:
            raise ValueError('No record found for the provided type, name and content')

        for existing_record in existing_records:
            if isinstance(existing_record['content'], list) and content is not None:
                # multiple values in record, just remove one value and only if it actually exist
                if content in existing_record['content']:
                    existing_record['content'].remove(content)
                    self._change_record_sets('UPSERT', existing_record['type'],
                                             existing_record['name'], existing_record['content'])
            else:
                # if only one record exist, or if content is not specified, remove whole record
                self._change_record_sets('DELETE', existing_record['type'],
                                         existing_record['name'], existing_record['content'])

        return True

    def _list_records(self, rtype=None, name=None, content=None):
        """List all records for the hosted zone."""
        records = self._list_record_sets(rtype, name, content)

        flatten_records = []
        for record in records:
            if isinstance(record['content'], list):
                for one_content in record['content']:
                    flatten_record = record.copy()
                    flatten_record['content'] = one_content
                    flatten_record['id'] = _identifier(flatten_record)
                    flatten_records.append(flatten_record)
            else:
                record['id'] = _identifier(record)
                flatten_records.append(record)

        LOGGER.debug('list_records: %s', records)

        return flatten_records

    def _list_record_sets(self, rtype=None, name=None, content=None):
        records = []
        paginator = RecordSetPaginator(self.r53_client, self.domain_id)
        for record in paginator.all_record_sets():
            record_content = []
            if rtype is not None and record['Type'] != rtype:
                continue
            if name is not None and record['Name'] != self._fqdn_name(name):
                continue
            if record.get('AliasTarget', None) is not None:
                record_content = [record['AliasTarget'].get('DNSName', None)]
            if record.get('ResourceRecords', None) is not None:
                record_content = [_format_content(record['Type'], value['Value']) for value
                                  in record['ResourceRecords']]
            if content is not None and content not in record_content:
                continue

            LOGGER.debug('record: %s', record)
            records.append({
                'type': record['Type'],
                'name': self._full_name(record['Name']),
                'ttl': record.get('TTL', None),
                'content': record_content[0] if len(record_content) == 1 else record_content,
            })
        return records

    def _request(self, action='GET', url='/', data=None, query_params=None):
        # Helper _request is not used in Route53 provider
        pass


def _format_content(rtype, content):
    return content[1:-1] if rtype in ['TXT', 'SPF'] else content


def _identifier(record):
    sha256 = hashlib.sha256()
    sha256.update(('type=' + record.get('type', '') + ',').encode('utf-8'))
    sha256.update(('name=' + record.get('name', '') + ',').encode('utf-8'))
    sha256.update(('data=' + record.get('data', '') + ',').encode('utf-8'))
    return sha256.hexdigest()[0:7]
