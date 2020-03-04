"""Provide support to Lexicon for AWS Route 53 DNS changes."""
from __future__ import absolute_import
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
              
    # Allow bypassing the zone-id lookup for complex use cases like delegated subdomain
    subparser.add_argument("--zone-id",
        help=("the AWS zone ID to use, should be something like A1B2ZABCDEFGHI"))

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
        # Allow setting domain_id from the command line
        self.domain_id = self._get_provider_option('zone_id') or None
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
        # if this was set via the command-line argument, we don't need to look it up
        if self.domain_id is None:
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
        value = '"{0}"'.format(content) if rtype in ['TXT', 'SPF'] else content
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
                                'ResourceRecords': [
                                    {
                                        'Value': value
                                    }
                                ]
                            }
                        }
                    ]
                }
            )
            return True
        except botocore.exceptions.ClientError as error:
            LOGGER.debug(str(error), exc_info=True)

    def _create_record(self, rtype, name, content):
        """Create a record in the hosted zone."""
        return self._change_record_sets('CREATE', rtype, name, content)

    def _update_record(self, identifier=None, rtype=None, name=None, content=None):
        """Update a record from the hosted zone."""
        return self._change_record_sets('UPSERT', rtype, name, content)

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """Delete a record from the hosted zone."""
        return self._change_record_sets('DELETE', rtype, name, content)

    def _format_content(self, rtype, content):  # pylint: disable=no-self-use
        return content[1:-1] if rtype in ['TXT', 'SPF'] else content

    def _list_records(self, rtype=None, name=None, content=None):
        """List all records for the hosted zone."""
        records = []
        paginator = RecordSetPaginator(self.r53_client, self.domain_id)
        for record in paginator.all_record_sets():
            if rtype is not None and record['Type'] != rtype:
                continue
            if name is not None and record['Name'] != self._fqdn_name(name):
                continue
            if record.get('AliasTarget', None) is not None:
                record_content = [record['AliasTarget'].get('DNSName', None)]
            if record.get('ResourceRecords', None) is not None:
                record_content = [self._format_content(record['Type'], value['Value']) for value
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
        LOGGER.debug('list_records: %s', records)
        return records

    def _request(self, action='GET', url='/', data=None, query_params=None):
        # Helper _request is not used in Route53 provider
        pass
