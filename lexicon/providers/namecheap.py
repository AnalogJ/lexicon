"""Module provider for Namecheap"""
from __future__ import absolute_import
import logging

from lexicon.providers.base import Provider as BaseProvider

try:
    # this module uses the optional `PyNamecheap` library from PyPi
    import namecheap  # optional dep
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = ['namecheap.com']


def provider_parser(subparser):
    """Configure provider parser for Namecheap"""
    subparser.add_argument(
        '--auth-token',
        help='specify api token for authentication'
    )

    # earlier versions of the API expected the email address here
    # now they appear to want the username.
    subparser.add_argument(
        '--auth-username',
        help='specify username for authentication'
    )

    # FIXME What is the client IP used for?
    # this doesn't seem to be used for anything, but is required by their API
    # namecheap requires API requests to come from whitelisted domains, and this
    # is probably updated with the actual IP on their end.
    subparser.add_argument(
        '--auth-client-ip',
        help='Client IP address to send to Namecheap API calls',
        default='127.0.0.1'
    )
    subparser.add_argument(
        '--auth-sandbox',
        help='Whether to use the sandbox server',
        action='store_true'
    )


class Provider(BaseProvider):
    """
    ========================================================================
    WARNING
    ========================================================================
    The Namecheap API does not add/update/delete a host but "gets" and
    "sets" ALL hosts at once (a complete replacement). In their comments on
    the API docs (https://www.namecheap.com/support/api/methods/domains-dns/set-hosts.aspx)
    it appears that not all host types are handled by their system.

    Their API only handles `[A, AAAA, CNAME, MX, MXE, TXT, URL, URL301, FRAME]`

    If you have SRV record, it may get lost. Also records configured as
    `A + DDNS` on their control panel will be downgrated to `A` records.
    """

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.client = namecheap.Api(
            ApiUser=self._get_provider_option('auth_username') or '',
            ApiKey=self._get_provider_option('auth_token') or '',
            UserName=self._get_provider_option('auth_username') or '',
            ClientIP=self._get_provider_option('auth_client_ip') or '',
            sandbox=self._get_provider_option('auth_sandbox') or False,
            debug=False,
        )
        self.domain = self.domain
        self.domain_id = None

    def _authenticate(self):
        """
        The Namecheap API is a little difficult to work with.
        Originally this method called PyNamecheap's `domains_getList`, which is
        connected to an API endpoint that only lists domains registered under
        the authenticating account. However, an authenticating Namecheap user
        may be permissioned to manage the DNS of additional domains. Namecheap's
        API does not offer a way to list these domains.

        This approach to detecting permissioned relies on some implementation
        details of the Namecheap API and the PyNamecheap module:

        * If the user does not own the domain, or is not permissioned to manage
          it in any way, Namecheap will return an error status, which
          PyNamecheap will instantly catch and raise.
        * If a non-error repsonse is returned, the XML payload is analyzed.
          If the user owns the domain it immediately returns valid. Otherwise
          we look for "All" Modification rights, or the hosts-edit permission.

        This is not feature complete and most-likely misses multiple scenarios
        where:
        * a user is privileged to manage the domain DNS, but via another "right"
        * a user is privileged to manage the domain, but DNS is not configured

        Important Note:
        * the Namecheap API has inconsistent use of capitalization with strings
          and a case-insensitive match should be made. e.g. the following appear
          in a payload: `False` and 'false', 'OK' and 'Ok'.

        TODO:
        * check payload for PremiumDNS
          <PremiumDnsSubscription>
            <IsActive>false</IsActive>
          </PremiumDnsSubscription>
        * check payload for other types of DNS
          <DnsDetails ProviderType="FREE" IsUsingOurDNS="true" HostCount="5"
                EmailType="No Email Service" DynamicDNSStatus="false" IsFailover="false">
            <Nameserver>dns1.registrar-servers.com</Nameserver>
            <Nameserver>dns2.registrar-servers.com</Nameserver>
          </DnsDetails>
        """
        extra_payload = {'DomainName': self.domain, }

        try:
            xml = self.client._call('namecheap.domains.getInfo', extra_payload)  # pylint: disable=protected-access
        except namecheap.ApiError as err:
            # this will happen if there is an API connection error
            # OR if the user is not permissioned to manage this domain
            # OR the API request came from a not whitelisted IP
            # we should print the error, so people know how to correct it.
            raise Exception('Authentication failed: `%s`' % str(err))

        xpath = './/{%(ns)s}CommandResponse/{%(ns)s}DomainGetInfoResult' % {
            'ns': namecheap.NAMESPACE}
        domain_info = xml.find(xpath)

        def _check_hosts_permission():
            # this shouldn't happen
            if domain_info is None:
                return False

            # do they own the domain?
            if domain_info.attrib['IsOwner'].lower() == 'true':
                return True

            # look for rights
            xpath_alt = ('.//{%(ns)s}CommandResponse/{%(ns)s}DomainGetInfoResult'
                         '/{%(ns)s}Modificationrights' % {'ns': namecheap.NAMESPACE})
            rights_info = xml.find(xpath_alt)
            if rights_info is None:
                return False

            # all rights
            if rights_info.attrib['All'].lower() == 'true':
                return True

            for right in rights_info.getchildren():
                if right.attrib['Type'].lower() == 'hosts':
                    # we're only looking at hosts, so we can exit now
                    return right.text.lower() == 'ok'

            return None

        permissioned = _check_hosts_permission()
        if not permissioned:
            raise Exception('The domain {} is not controlled by this Namecheap '
                            'account'.format(self.domain))

        # FIXME What is this for?
        self.domain_id = self.domain

    def option_ttl(self):
        """
        Parse the `options` for a TTL.
        Used as a distinct function for documentation.
        via https://www.namecheap.com/support/api/methods/domains-dns/set-hosts.aspx
            Time to live for all record types.
            Possible values: any value between 60 to 60000
            Default Value: 1800
        if a TTL is submitted on the commandline:
            this will parse, but not validate it
        if no TTL is submitted:
            it will be ignored, allowing the server-side default
        Please note:
            Namecheap appears to have an internal cache on records; even with a
            short TTL of 60 seconds, it may take 120 seconds for their DNS to
            propagate.
        """
        return self._get_lexicon_option('ttl')

    # Create record. If record already exists with the same content, do nothing
    def _create_record(self, rtype, name, content):
        record = {
            # required
            'Type': rtype,
            'Name': self._relative_name(name),
        }

        # MX records needd special treatment
        if rtype == 'MX':
            mxpref, address = content.split()
            record.update({
                'MxPref': int(mxpref),
                'Address': address
            })
        else:
            record.update({'Address': content})

        # inject the ttl if specified
        option_ttl = self.option_ttl()
        if option_ttl:
            record['TTL'] = option_ttl
        # LOGGER.debug('create_record: %s', 'id' in payload)
        # return 'id' in payload
        self.client.domains_dns_addHost(self.domain, record)
        return True

    # List all records. Return an empty list if no records found.
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is
    # received.
    def _list_records(self, rtype=None, name=None, content=None):
        return self._list_records_internal(rtype=rtype, name=name, content=content)

    def _list_records_internal(self, rtype=None, name=None, content=None, identifier=None):
        records = []
        raw_records = self.client.domains_dns_getHosts(self.domain)
        for record in raw_records:
            records.append(self._convert_to_lexicon(record))

        if identifier:
            records = [record for record in records if record['id'] == identifier]
        if rtype:
            records = [record for record in records if record['type'] == rtype]
        if name:
            if name.endswith('.'):
                name = name[:-1]
            records = [record for record in records if name in record['name']]
        if content:
            records = [
                record for record in records if record['content'].lower() == content.lower()]

        LOGGER.debug('list_records: %s', records)
        return records

    # Create or update a record.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        # Delete record if it exists
        self._delete_record(identifier, rtype, name, content)
        return self._create_record(rtype, name, content)

    # Delete an existing record.
    # If record does not exist, do nothing.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        records = self._list_records_internal(
            rtype=rtype, name=name, content=content, identifier=identifier)
        for record in records:
            self.client.domains_dns_delHost(
                self.domain, self._convert_to_namecheap(record))
        return True

    def _convert_to_namecheap(self, record):
        """ converts from lexicon format record to namecheap format record,
        suitable to sending through the api to namecheap"""

        processed_record = {}

        name = record['name']
        if name.endswith('.'):
            name = name[:-1]

        short_name = name[:name.find(self.domain) - 1]

        if record['type'] == 'MX':
            # MX records needs to have separate treatment.
            mxpref, address = record['content'].split()
            processed_record.update({
                'MxPref': mxpref,
                'Address': address
            })
        else:
            processed_record.update({
                'Address': record['content']})

        processed_record.update({
            'Type': record['type'],
            'Name': short_name,
            'TTL': record['ttl'],
            'HostId': record['id']
        })

        return processed_record

    def _convert_to_lexicon(self, record):
        """ converts from namecheap raw record format to lexicon format record
        """

        name = record['Name']

        if not name.endswith(self.domain):
            name += ".{}".format(self.domain)

        content = '{} {}'.format(record['MXPref'], record['Address']) \
            if record['Type'] == 'MX' else record['Address']

        processed_record = {
            'type': record['Type'],
            'name': name,
            'ttl': record['TTL'],
            'content': content,
            'id': record['HostId']
        }

        return processed_record

    def _request(self, action='GET', url='/', data=None, query_params=None):
        # Helper _request is not used by Namecheap provider
        pass
