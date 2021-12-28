"""
===============================
Module provider for ValueDomain
===============================


Value-Domain API
================

Reference: https://www.value-domain.com/vdapi/

- Preparation

1. Get your auth token: https://www.value-domain.com/vdapi/
2. export LEXICON_VALUEDOMAIN_AUTH_TOKEN="<Your Auth Token>"
3. export DOMAIN_NAME=$(curl -s https://api.value-domain.com/v1/domains -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -c "import sys,json;print(json.load(sys.stdin)['results'][0]['domainname'])")

- Get list of your domain information

curl -s https://api.value-domain.com/v1/domains -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -m json.tool

- Get domain name

curl -s https://api.value-domain.com/v1/domains -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -c "import sys,json;print(json.load(sys.stdin)['results'][0]['domainname'])"

- Get name servers

curl -s https://api.value-domain.com/v1/domains/nameserver -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -m json.tool
curl -s https://api.value-domain.com/v1/domains/${DOMAIN_NAME}/nameserver -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -m json.tool

- Get DNS records

curl -s https://api.value-domain.com/v1/domains/dns -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -m json.tool
curl -s https://api.value-domain.com/v1/domains/${DOMAIN_NAME}/dns -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -m json.tool

- Get API Logs

curl -s https://api.value-domain.com/v1/logs -H "Authorization: Bearer ${LEXICON_VALUEDOMAIN_AUTH_TOKEN}" | python -m json.tool


Value Doamin DNS records syntax
===============================

Reference: https://www.value-domain.com/moddnsfree.php

- A record
  - a www 123.123.123.3                : A record for www.<YOUR-DOMAIN>
  - a * 123.123.123.5                  : A record for any sub domain of <YOUR-DOMAIN>
  - a @ 123.123.123.5                  : A record for <YOUR-DOMAIN> (no sub domain)

- AAAA record
  - aaaa ipv6 FF01::101                : AAAA record for ipv6.<YOUR-DOMAIN>

- MX record
  - mx mx1.your.domain. 10             : MX record for <YOUR-DOMAIN> (Server:mx1.your.domain, Priority 10)
  - mx @ 10                            : MX record for <YOUR-DOMAIN> (Server:<YOUR-DOMAIN>, Priority 10)

- NS record
  - ns abc ns1.example.com.            : NS record for abc.<YOUR-DOMAIN>

- TXT record
  - txt abc v=spf1 mx ~all             : TXT record for abc.<YOUR-DOMAIN> (v=spf1 mx ~all)
  - txt @ v=spf1 mx ~all               : TXT record for <YOUR-DOMAIN> (v=spf1 mx ~all)

- SRV record
  - srv _smtp._tcp 1 2 25 server1.your.domain   : SRV record for _smtp._tcp.<YOUR-DOMAIN> (Priority:1, Weight:2, Port:25)
"""

import hashlib
import json
import logging
import time
from http import cookiejar
from http.client import HTTPResponse
from typing import Any, Callable, Dict, List, NamedTuple, Optional, TypeVar, Union
from urllib import request
from urllib.error import HTTPError
from urllib.request import OpenerDirector

from lexicon.providers.base import Provider as BaseProvider

T = TypeVar("T")

LOGGER = logging.getLogger(__name__)
NAMESERVER_DOMAINS = ["value-domain.com"]

DEFAULT_TTL = 3600

########################################################################
# Util
########################################################################


def convert_json_to_bytes(x):
    return bytes(json.dumps(x), "utf-8")


def is_domain(target: str) -> bool:
    return (
        len(target) > 1
        and len(target.strip(".")) > 0
        and target[0] != "."
        and target[-1] == "."
    )


def is_sub_domain(target: str, domainname: str) -> Union[str, bool]:
    idx = target.rfind(domainname)
    return (
        target[0:idx].strip(".")
        if idx >= 0 and is_domain(target) and idx + len(domainname) + 1 == len(target)
        else False
    )


########################################################################
# Rest API
########################################################################


class RestApiResponse(NamedTuple):
    header: HTTPResponse
    data: bytes


RESTAPI_CALLER_TYPE = Callable[[str, str, Optional[T]], RestApiResponse]


def reastapi_add_content_type(
    _headers: Optional[Dict[str, str]],
    content_type: Optional[str],
    content: Optional[bytes],
) -> Dict[str, str]:
    """Add 'Content-Type' header if exists"""
    headers = _headers.copy() if _headers is not None else {}
    if content_type is not None and content is not None and len(content) != 0:
        headers["Content-Type"] = content_type
    return headers


def restapi_create_request(
    url: str,
    method: str,
    headers: Optional[Dict[str, str]],
    content_type: Optional[str],
    content: Optional[bytes],
) -> request.Request:
    """Create Request instance including content if exists"""
    return request.Request(
        url,
        data=content if content is not None and len(content) > 0 else None,
        method=method,
        headers=reastapi_add_content_type(headers, content_type, content),
    )


def restapi_call(
    opener: OpenerDirector,
    url: str,
    method: str,
    headers: Optional[Dict[str, str]],
    content_type: Optional[str] = None,
    content: Optional[bytes] = None,
) -> RestApiResponse:
    """Execute HTTP Request with OpenerDirector"""
    with opener.open(
        restapi_create_request(url, method, headers, content_type, content)
    ) as response:
        return RestApiResponse(response, response.read())


def restapi_build_opener() -> OpenerDirector:
    """Create OpenerDirector instance with cookie processor"""
    return request.build_opener(
        request.BaseHandler(), request.HTTPCookieProcessor(cookiejar.CookieJar())
    )


def restapi_exception_not_200(response: HTTPResponse):
    # HTTPError will be raised if status >= 400
    if response.status != 200:
        LOGGER.error(f"HTTP Status: {response.status}")
        raise Exception(f"HTTP Status: {response.status}")


########################################################################
# Value Domain API
########################################################################


VDAPI_ENDPOINT = "https://api.value-domain.com/v1"


class RecordData(NamedTuple):
    rtype: str
    name: str
    content: str

    def __eq__(self, other):
        return (
            self.rtype.lower() == other.rtype.lower()
            and self.name.lower() == other.name.lower()
            and self.content == other.content
        )

    def __str__(self):
        return f"{self.rtype.lower()} {self.name.lower()} {self.content}"

    def match(
        self,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ) -> bool:
        return (
            (rtype is None or rtype.lower() == self.rtype.lower())
            and (name is None or name.lower() == self.name.lower())
            and (content is None or content.lower() == self.content.lower())
        )

    def id(self):
        return hashlib.md5(str(self).encode("utf-8")).hexdigest()


class DomainData(NamedTuple):
    records: List[RecordData]
    ttl: int


def vdapi_build_caller(
    opener: OpenerDirector,
    content_type: str,
    headers: Optional[Dict[str, str]] = None,
    content_decoder=lambda x: x,
) -> RESTAPI_CALLER_TYPE:
    def _(
        url: str, method: str, content: Optional[T] = None, interval=1
    ) -> RestApiResponse:
        try:
            return restapi_call(
                opener,
                url,
                method,
                headers,
                content_type,
                content_decoder(content) if content is not None else None,
            )
        except HTTPError as http_error:
            if http_error.code == 429:  # Too much Request
                time.sleep(interval)
                return _(url, method, content, interval * 2)
            else:
                raise http_error

    return _


def vdapi_create_caller(auth_token: str):
    return vdapi_build_caller(
        restapi_build_opener(),
        "application/json",
        {
            # Value-Domain API rejects the request with default Python User-Agent.
            "User-Agent": "curl/7.74.0",
            "Cache-Control": "no-cache, no-store",
            "Authorization": f"Bearer {auth_token}",
        },
        convert_json_to_bytes,
    )


def vdapi_get_domain_list(caller: RESTAPI_CALLER_TYPE) -> List[str]:
    resp: RestApiResponse = caller(f"{VDAPI_ENDPOINT}/domains", "GET", None)
    restapi_exception_not_200(resp.header)
    return list(
        filter(
            lambda x: x is not None,
            [
                domain.get("domainname")
                for domain in json.loads(resp.data.decode("utf-8").strip()).get(
                    "results"
                )
            ],
        )
    )


def vdapi_get_domain_data(
    caller: RESTAPI_CALLER_TYPE, domainname: str
) -> Optional[DomainData]:
    resp: RestApiResponse = caller(
        f"{VDAPI_ENDPOINT}/domains/{domainname}/dns", "GET", None
    )
    restapi_exception_not_200(resp.header)
    domain_info: dict = json.loads(resp.data.decode("utf-8").strip())
    domain_records: Optional[str] = domain_info.get("results", {}).get("records")
    return (
        DomainData(
            [
                RecordData(elem[0], elem[1], elem[2])
                for elem in [line.split(" ", 3) for line in domain_records.split("\n")]
                if len(elem) == 3
            ],
            int(domain_info.get("results", {}).get("ttl", DEFAULT_TTL)),
        )
        if domain_records is not None
        else None
    )


def vdapi_set_domain_data(
    caller: RESTAPI_CALLER_TYPE, domainname: str, data: DomainData
):
    resp = caller(
        f"{VDAPI_ENDPOINT}/domains/{domainname}/dns",
        "PUT",
        {
            "ns_type": "valuedomain1",
            "records": "\n".join([str(record) for record in data.records]),
            "ttl": data.ttl,
        },
    )
    restapi_exception_not_200(resp.header)


########################################################################
# Lexicon Provider for Value-Domain
########################################################################


def provider_parser(subparser):
    """Configure provider parser for Value Domain"""
    subparser.description = """
        Value Domain requires a token to access its API.
        You can generate one for your account on the following URL:
        https://www.value-domain.com/vdapi/"""
    subparser.add_argument("--auth-token", help="specify youyr API token")


class Provider(BaseProvider):
    """Provider class for Value Domain"""

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id: Optional[list[str]] = None

        auth_token = self._get_provider_option("auth_token")
        assert auth_token is not None, "No authenticaion token defined"

        self.caller: RESTAPI_CALLER_TYPE = vdapi_create_caller(auth_token)

    # Authenticate against provider,
    # Make any requests required to get the domain's id for this provider,
    # so it can be used in subsequent calls.
    # Should throw an error if authentication fails for any reason,
    # of if the domain does not exist.
    def _authenticate(self):
        self.domain_id = vdapi_get_domain_list(self.caller)

        assert len(self.domain_id) > 0, "Failed to get domain names"
        if self.domain not in self.domain_id:
            raise Exception(f"{self.domain} not managed")

    # Create record. If record already exists with the same content, do nothing'
    def _create_record(self, rtype: str, name: str, content: str):
        self._assert_initialized()
        ttl_option = self._get_lexicon_option("ttl")
        domain_data = vdapi_get_domain_data(self.caller, self.domain)
        rec = self._create_record_data(rtype, self._relative_name(name), content)

        if domain_data is not None and rec not in domain_data.records:
            vdapi_set_domain_data(
                self.caller,
                self.domain,
                DomainData(
                    domain_data.records + [rec],
                    ttl_option
                    if ttl_option is not None and ttl_option > 0
                    else DEFAULT_TTL
                    if ttl_option is not None
                    else domain_data.ttl,
                ),
            )
        elif domain_data is not None:
            pass
        else:
            vdapi_set_domain_data(
                self.caller,
                self.domain,
                DomainData(
                    [rec],
                    ttl_option
                    if ttl_option is not None and ttl_option > 0
                    else DEFAULT_TTL,
                ),
            )

        return True

    # List all records. Return an empty list if no records found
    # type, name and content are used to filter records.
    # If possible filter during the query, otherwise filter after response is received.
    def _list_records(
        self,
        rtype: Optional[str] = None,
        name: Optional[str] = None,
        content: Optional[str] = None,
    ):
        self._assert_initialized()
        domain_data = vdapi_get_domain_data(self.caller, self.domain)
        return (
            [
                {
                    "id": record_data.id(),
                    "ttl": domain_data.ttl,
                    "type": record_data.rtype.upper(),
                    "name": self._fqdn_name(record_data.name)
                    if record_data.rtype.lower() != "txt"
                    else self._full_name(record_data.name),
                    "content": record_data.content,
                }
                for record_data in domain_data.records
                if record_data.match(
                    rtype,
                    self._relative_name(name) if name is not None else None,
                    content,
                )
            ]
            if domain_data is not None
            else []
        )

    # Update a record. Identifier must be specified.
    def _update_record(self, identifier, rtype=None, name=None, content=None):
        self._assert_initialized()
        ttl_option = self._get_lexicon_option("ttl")
        domain_data = vdapi_get_domain_data(self.caller, self.domain)
        target = [record for record in domain_data.records if record.id() == identifier]

        if len(target) > 0:
            vdapi_set_domain_data(
                self.caller,
                self.domain,
                DomainData(
                    [
                        record
                        for record in domain_data.records
                        if record.id() != identifier
                    ]
                    + [
                        self._create_record_data(
                            rtype or target[0].rtype,
                            name or self._relative_name(target[0].name),
                            content or target[0].content,
                        )
                    ],
                    ttl_option
                    if ttl_option is not None and ttl_option > 0
                    else DEFAULT_TTL
                    if ttl_option is not None
                    else domain_data.ttl,
                ),
            )

        return True

    # Delete an existing record.
    # If record does not exist, do nothing.
    # If an identifier is specified, use it, otherwise do a lookup using type, name and content.
    def _delete_record(self, identifier=None, rtype=None, name=None, content=None):
        self._assert_initialized()
        domain_data = vdapi_get_domain_data(self.caller, self.domain)
        if domain_data is not None and identifier is not None:
            vdapi_set_domain_data(
                self.caller,
                self.domain,
                DomainData(
                    [
                        record
                        for record in domain_data.records
                        if record.id() != identifier
                    ],
                    domain_data.ttl,
                ),
            )
        elif domain_data is not None:
            vdapi_set_domain_data(
                self.caller,
                self.domain,
                DomainData(
                    [
                        record
                        for record in domain_data.records
                        if not record.match(rtype, self._relative_name(name), content)
                    ],
                    domain_data.ttl,
                ),
            )

        return True

    def _request(
        self,
        action: str = "GET",
        url: str = "/",
        data: Optional[Dict] = None,
        query_params: Optional[Dict] = None,
    ) -> Any:
        pass

    #        self._assert_initialized()
    #        return self.caller(url, action, data)

    def _assert_initialized(self):
        if self.caller is None or self.domain_id is None:
            self._authenticate()

        assert self.caller is not None, "HTTP caller not defined"
        assert self.domain_id is not None or len(
            self.domain_id == 0
        ), "Domain name not retriebed"

    def _create_record_data(self, rtype: str, name: str, content: str) -> RecordData:
        return RecordData(rtype.lower(), self._relative_name(name).lower(), content)


if __name__ == "__main__":
    import os
    import unittest

    DUMMY_TYPE = "a"
    DUMMY_NAME = "test"
    DUMMY_CONTENT = "1.2.3.4"
    DUMMY_CONTENT2 = "2.3.4.5"

    class TestValueDomain(unittest.TestCase):
        def setUp(self):
            self.auth_token = os.environ.get("LEXICON_VALUEDOMAIN_AUTH_TOKEN")
            if self.auth_token is None:
                raise Exception("LEXICON_VALUEDOMAIN_AUTH_TOKEN not defined")
            self.caller = vdapi_create_caller(self.auth_token)

        def tearDown(self):
            pass

        def _create_provide(self, domainname: str):
            return Provider(
                {
                    "provider_name": "valuedomain",
                    "domain": domainname,
                    "valuedomain": {"auth_token": self.auth_token},
                }
            )

        def test_vdapi_get_domain_list(self):
            domain_list = vdapi_get_domain_list(self.caller)
            self.assertGreater(len(domain_list), 0)

        def test_vdapi_get_record_list(self):
            domain_list = vdapi_get_domain_list(self.caller)
            for domainname in domain_list:
                record = vdapi_get_domain_data(self.caller, domainname)

                self.assertIsNotNone(record)
                self.assertGreater(len(record.records), 0)
                self.assertIsNotNone(record.ttl)

        def test_vdapi_set_record_list(self):
            domain_list = vdapi_get_domain_list(self.caller)
            for domainname in domain_list:
                domain_data = vdapi_get_domain_data(self.caller, domainname)
                dummy = RecordData(DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT)
                vdapi_set_domain_data(
                    self.caller,
                    domainname,
                    DomainData(domain_data.records + [dummy], domain_data.ttl),
                )
                updated_domain_data = vdapi_get_domain_data(self.caller, domainname)
                self.assertIn(dummy, updated_domain_data.records)

                # cleanup
                vdapi_set_domain_data(self.caller, domainname, domain_data)
                updated_domain_data = vdapi_get_domain_data(self.caller, domainname)
                self.assertNotIn(dummy, updated_domain_data.records)

        def test_list_records(self):
            domain_list = vdapi_get_domain_list(self.caller)
            for domainname in domain_list:
                provider = self._create_provide(domainname)
                provider._authenticate()

                records = provider._list_records()
                self.assertGreater(len(records), 0)

                records = provider._list_records(rtype="A")
                self.assertGreater(len(records), 0)

                records = provider._list_records(rtype="B")
                self.assertEqual(len(records), 0)

        def test_create_records(self):
            domain_list = vdapi_get_domain_list(self.caller)
            for domainname in domain_list:
                provider = self._create_provide(domainname)
                provider._authenticate()

                provider._create_record(DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT)
                records = provider._list_records(
                    rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                )
                self.assertGreater(len(records), 0)

                provider._create_record(
                    DUMMY_TYPE, f"{DUMMY_NAME}.{domainname}.", DUMMY_CONTENT
                )
                self.assertEqual(
                    len(
                        provider._list_records(
                            rtype=DUMMY_TYPE,
                            name=f"DUMMY_NAME.{domainname}.",
                            content=DUMMY_CONTENT,
                        )
                    ),
                    0,
                )

                # cleanup
                provider._delete_record(None, DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT)
                self.assertEqual(
                    len(
                        provider._list_records(
                            rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                        )
                    ),
                    0,
                )

        def test_delete_records_by_id(self):
            domain_list = vdapi_get_domain_list(self.caller)
            for domainname in domain_list:
                provider = self._create_provide(domainname)
                provider._authenticate()

                provider._create_record(DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT)
                recl = provider._list_records(
                    rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                )
                self.assertGreater(len(recl), 0)
                provider._delete_record(identifier=recl[0].get("id"))
                self.assertEqual(
                    len(
                        provider._list_records(
                            rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                        )
                    ),
                    0,
                )

        def test_delete_records_by_data(self):
            domain_list = vdapi_get_domain_list(self.caller)
            for domainname in domain_list:
                provider = self._create_provide(domainname)
                provider._authenticate()

                provider._create_record(DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT)
                recl = provider._list_records(
                    rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                )
                self.assertGreater(len(recl), 0)
                provider._delete_record(None, DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT)
                self.assertEqual(
                    len(
                        provider._list_records(
                            rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                        )
                    ),
                    0,
                )

        def test_update_record(self):
            domain_list = vdapi_get_domain_list(self.caller)
            for domainname in domain_list:

                provider = self._create_provide(domainname)
                provider._authenticate()

                provider._create_record(DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT)
                recl = provider._list_records(
                    rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                )
                self.assertGreater(len(recl), 0)
                provider._update_record(
                    identifier=recl[0].get("id"), content=DUMMY_CONTENT2
                )
                self.assertGreater(
                    len(
                        provider._list_records(
                            rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT2
                        )
                    ),
                    0,
                )

                # cleanup
                provider._delete_record(None, DUMMY_TYPE, DUMMY_NAME, DUMMY_CONTENT2)
                self.assertEqual(
                    len(
                        provider._list_records(
                            rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT
                        )
                    ),
                    0,
                )
                self.assertEqual(
                    len(
                        provider._list_records(
                            rtype=DUMMY_TYPE, name=DUMMY_NAME, content=DUMMY_CONTENT2
                        )
                    ),
                    0,
                )

    unittest.main()
