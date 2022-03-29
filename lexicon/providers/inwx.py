"""Module provider for INWX"""
import logging

from lexicon.exceptions import AuthenticationError
from lexicon.providers.base import Provider as BaseProvider

try:
    import xmlrpclib  # type: ignore
except ImportError:
    import xmlrpc.client as xmlrpclib  # type: ignore

LOGGER = logging.getLogger(__name__)

NAMESERVER_DOMAINS = [
    "ns.inwx.de",
    "ns2.inwx.de",
    "ns3.inwx.eu",
    "ns4.inwx.com",
    "ns5.inwx.net",
    "ns.domrobot.com",
    "ns.domrobot.net",
    "ns.domrobot.org",
    "ns.domrobot.info",
    "ns.domrobot.biz",
]


def provider_parser(subparser):
    """Configure provider parser for INWX"""
    subparser.add_argument(
        "--auth-username", help="specify username for authentication"
    )
    subparser.add_argument(
        "--auth-password", help="specify password for authentication"
    )


class Provider(BaseProvider):
    """
    INWX offers a free testing system on https://ote.inwx.com
    see https://www.inwx.de/en/offer/api for details about ote and the api
    """

    def __init__(self, config):
        """
        :param config: command line options
        """
        super(Provider, self).__init__(config)

        self._auth = {
            "user": self._get_provider_option("auth_username"),
            "pass": self._get_provider_option("auth_password"),
        }
        self._domain = self.domain.lower()
        self.domain_id = None

        endpoint = (
            self._get_provider_option("endpoint") or "https://api.domrobot.com/xmlrpc/"
        )

        self._api = xmlrpclib.ServerProxy(endpoint, allow_none=True)

    def _validate_response(self, response, message, exclude_code=None):
        """
        validate an api server response

        :param dict response: server response to check
        :param str message: error message to raise
        :param int exclude_code: error codes to exclude from errorhandling
        :return:
        ":raises Exception: on error
        """
        if "code" in response and response["code"] >= 2000:
            if exclude_code is not None and response["code"] == exclude_code:
                return

            raise Exception(f"{message}: {response['msg']} ({response['code']})")

    # Make any request to validate credentials
    def _authenticate(self):
        """
        run any request against the API just to make sure the credentials
        are valid

        :return bool: success status
        :raises Exception: on error
        """
        opts = {"domain": self._domain}
        opts.update(self._auth)
        response = self._api.nameserver.info(opts)
        try:
            self._validate_response(response=response, message="Failed to authenticate")
        except Exception as e:
            raise AuthenticationError(str(e))

        # set to fake id to pass tests, inwx doesn't work on domain id but
        # uses domain names for identification
        self.domain_id = 1

        return True

    def _create_record(self, rtype, name, content):
        """
        create a record
        does nothing if the record already exists

        :param str rtype: type of record
        :param str name: name of record
        :param mixed content: value of record
        :return bool: success status
        :raises Exception: on error
        """
        opts = {
            "domain": self._domain,
            "type": rtype.upper(),
            "name": self._full_name(name),
            "content": content,
        }
        if self._get_lexicon_option("ttl"):
            opts["ttl"] = self._get_lexicon_option("ttl")
        opts.update(self._auth)

        response = self._api.nameserver.createRecord(opts)
        self._validate_response(
            response=response, message="Failed to create record", exclude_code=2302
        )

        return True

    def _list_records(self, rtype=None, name=None, content=None):
        """
        list all records

        :param str rtype: type of record
        :param str name: name of record
        :param mixed content: value of record
        :return list: list of found records
        :raises Exception: on error
        """
        opts = {"domain": self._domain}
        if rtype is not None:
            opts["type"] = rtype.upper()
        if name is not None:
            opts["name"] = self._full_name(name)
        if content is not None:
            opts["content"] = content
        opts.update(self._auth)

        response = self._api.nameserver.info(opts)
        self._validate_response(response=response, message="Failed to get records")

        records = []
        if "record" in response["resData"]:
            for record in response["resData"]["record"]:
                processed_record = {
                    "type": record["type"],
                    "name": record["name"],
                    "ttl": record["ttl"],
                    "content": record["content"],
                    "id": record["id"],
                }
                records.append(processed_record)

        return records

    def _update_record(self, identifier, rtype=None, name=None, content=None):
        """
        update a record

        :param int identifier: identifier of record to update
        :param str rtype: type of record
        :param str name: name of record
        :param mixed content: value of record
        :return bool: success status
        :raises Exception: on error
        """
        record_ids = []
        if not identifier:
            records = self._list_records(rtype, name)
            record_ids = [record["id"] for record in records]
        else:
            record_ids.append(identifier)

        for an_identifier in record_ids:
            opts = {"id": an_identifier}
            if rtype is not None:
                opts["type"] = rtype.upper()
            if name is not None:
                opts["name"] = self._full_name(name)
            if content is not None:
                opts["content"] = content
            opts.update(self._auth)

            response = self._api.nameserver.updateRecord(opts)
            self._validate_response(
                response=response, message="Failed to update record", exclude_code=2302
            )

        return True

    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        """
        delete a record
        filter selection to delete by identifier or rtype/name/content

        :param int identifier: identifier of record to update
        :param str rtype: rtype of record
        :param str name: name of record
        :param mixed content: value of record
        :return bool: success status
        :raises Exception: on error
        """
        record_ids = []
        if not identifier:
            records = self._list_records(rtype, name, content)
            record_ids = [record["id"] for record in records]
        else:
            record_ids.append(identifier)

        for record_id in record_ids:
            opts = {"id": record_id}
            opts.update(self._auth)
            response = self._api.nameserver.deleteRecord(opts)
            self._validate_response(
                response=response, message="Failed to update record"
            )

        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        # Helper _request is not used for INWX provider.
        pass
