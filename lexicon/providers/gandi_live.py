"""Provide support to Lexicon for Gandi LiveDNS changes.

Lexicon provides a common interface for querying and managing DNS services
through those services' APIs. This module implements the Lexicon interface
against the Gandi API.

Gandi introduced the LiveDNS API (http://doc.livedns.gandi.net/) in 2017.
It is the successor of the traditional DNS API, which suffered from long
delays between API-based changes and their activation.
The LiveDNS API has one significant peculiarity: DNS records with the
same name and type are managed as one unit. Thus records cannot be
addressed distinctly, which complicates removal of records significantly.

Note that Gandi domains can share zone configurations. In other words,
I can have domain-a.com and domain-b.com which share the same zone
configuration file. If I make changes to domain-a.com, those changes
will only apply to domain-a.com, as domain-b.com will continue using
the previous version of the zone configuration. This module makes no
attempt to detect and account for that.
"""

from __future__ import absolute_import

import json
import logging

from .base import Provider as BaseProvider

import requests

logger = logging.getLogger(__name__)


def ProviderParser(subparser):
    """Specify arguments for Gandi Lexicon Provider."""
    subparser.add_argument('--auth-token', help="specify Gandi API key")


class Provider(BaseProvider):
    """Provide Gandi DNS API implementation of Lexicon Provider interface.

    The class will use the following environment variables to configure
    it instance. For more information, read the Lexicon documentation.

    - LEXICON_GANDI_API_ENDPOINT - the Gandi API endpoint to use
      The default is the production URL https://rpc.gandi.net/xmlrpc/.
      Set this environment variable to the OT&E URL for testing.

    """

    def __init__(self, options, engine_overrides=None):
        super(Provider, self).__init__(options)
        self.domain_id = None
        self.api_endpoint = (options or {}).get(
            'api_endpoint', 'https://dns.api.gandi.net/api/v5')

    def authenticate(self):
        self._get('/domains/{0}'.format(self.options['domain']))
        self.domain_id = self.options['domain'].lower()

    def create_record(self, type, name, content):
        current_values = [record['content'] for record in self.list_records(type=type, name=name)]
        if current_values != [content]:
            # a change is necessary
            url = '/domains/{0}/records/{1}/{2}'.format(self.domain_id, self._relative_name(name),
                                                        type)
            if current_values:
                record = {'rrset_values': current_values + [content]}
                self._put(url, record)
            else:
                record = {'rrset_values': [content]}
                # add the ttl, if this is a new record
                if self.options.get('ttl'):
                    record['rrset_ttl'] = self.options.get('ttl')
                self._post(url, record)
        logger.debug('create_record: %s', True)
        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def list_records(self, type=None, name=None, content=None):
        """List all record for the domain in the active Gandi zone."""
        try:
            if name is not None:
                if type is not None:
                    query_results = [self._get(
                        '/domains/{0}/records/{1}/{2}'
                        .format(self.domain_id, self._relative_name(name), type))]
                else:
                    query_results = self._get('/domains/{0}/records/{1}'
                                              .format(self.domain_id, self._relative_name(name)))
            else:
                query_results = self._get('/domains/{0}/records'.format(self.domain_id))
                if type is not None:
                    query_results = [item for item in query_results if item['type'] == type]
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                query_results = []
            else:
                raise
        # convert records with multiple values into single-value records
        records = []
        for query_result in query_results:
            for value in query_result['rrset_values']:
                record = {
                    'type': query_result['rrset_type'],
                    'name': self._fqdn_name(query_result['rrset_name']),
                    'ttl': query_result['rrset_ttl'],
                    'content': value,
                    'id': query_result['rrset_name'],
                }
                # cleanup potential quoting if suitable
                self._clean_TXT_record(record)
                records.append(record)
        # filter for content, if requested
        if content is not None:
            records = [record for record in records if record['content'] == content]
        logger.debug('list_records: %s', records)
        return records

    # Update a record. Identifier must be specified.
    def update_record(self, identifier, type=None, name=None, content=None):
        """Updates the specified record in a new Gandi zone

        'content' should be a string or a list of strings
        """
        data = {}
        if type:
            data['rrset_type'] = type
        if name:
            data['rrset_name'] = self._relative_name(name)
        if content:
            if isinstance(content, (list, tuple, set)):
                data['rrset_values'] = list(content)
            else:
                data['rrset_values'] = [content]
        if type is None:
            # replace the records of a specific type
            url = '/domains/{0}/records/{1}/{2}'.format(self.domain_id,
                                                        identifier or self._relative_name(name),
                                                        type)
            self._put(url, data)
        else:
            # replace all records with a matching name
            url = '/domains/{0}/records/{1}'.format(self.domain_id,
                                                    identifier or self._relative_name(name))
            self._put(url, {'items': [data]})
        logger.debug('update_record: %s', True)
        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    def delete_record(self, identifier=None, type=None, name=None, content=None):
        remove_count = 0
        if not identifier:
            # get all matching (by type and name) records - ignore 'content' for now
            records = self.list_records(type=type, name=name)
            for current_type in set(record['type'] for record in records):
                matching_records = [record for record in records if record['type'] == current_type]
                # collect all non-matching values
                if content is None:
                    remaining_values = []
                else:
                    remaining_values = [record['content'] for record in matching_records
                                        if record['content'] != content]
                url = '/domains/{0}/records/{1}/{2}'.format(
                    self.domain_id, self._relative_name(name), current_type)
                if len(matching_records) == len(remaining_values):
                    # no matching item should be removed for this type
                    pass
                elif remaining_values:
                    # reduce the list of values
                    self._put(url, {'rrset_values': remaining_values})
                    remove_count += 1
                else:
                    # remove the complete record (possibly with multiple values)
                    self._delete(url)
                    remove_count += 1
        else:
            self._delete('/domains/{0}/records/{1}'.format(self.domain_id, identifier))
        if remove_count == 0:
            raise Exception('Record identifier could not be found.')

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
            'X-Api-Key': self.options.get('auth_token')
        }
        if not url.startswith(self.api_endpoint):
            url = self.api_endpoint + url

        r = requests.request(action, url, params=query_params,
                             data=json.dumps(data),
                             headers=default_headers)
        # if the request fails for any reason, throw an error.
        r.raise_for_status()
        if action == 'DELETE':
            return ''
        else:
            return r.json()
