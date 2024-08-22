import json
import logging
from argparse import ArgumentParser
from typing import List

from lexicon.exceptions import AuthenticationError
from lexicon.interfaces import Provider as BaseProvider

# tencentcloud-sdk-python is an optional dependency of lexicon; do not throw an ImportError if
# the dependency is unmet.
try:
    from tencentcloud.common import credential  # type: ignore
    from tencentcloud.dnspod.v20210323 import dnspod_client, models  # type: ignore
except ImportError:
    pass

LOGGER = logging.getLogger(__name__)


class Provider(BaseProvider):
    """Provider class for QCloud"""

    @staticmethod
    def get_nameservers() -> List[str]:
        return ["dnspod.tencentcloudapi.com"]

    @staticmethod
    def configure_parser(parser: ArgumentParser) -> None:
        parser.add_argument("--secret_id", help="specify secret_id for authentication")
        parser.add_argument(
            "--secret_key", help="specify secret_key for authentication"
        )

    def __init__(self, config):
        super(Provider, self).__init__(config)
        self.domain_id = None
        secret_id = self._get_provider_option("secret_id")
        secret_key = self._get_provider_option("secret_key")
        if not secret_id:
            raise Exception("Error, application secret_id is not defined")

        if not secret_key:
            raise Exception("Error, application secret_key is not defined")

        self.cred = credential.Credential(secret_id, secret_key)
        self.client = dnspod_client.DnspodClient(self.cred, "")
        # add support for other api entrypoints

    def authenticate(self):
        describe_domain_req = models.DescribeDomainListRequest()
        params = {
            "Keyword": self.domain,
        }
        describe_domain_req.from_json_string(json.dumps(params))
        describe_domain_resp = self.client.DescribeDomainList(describe_domain_req)
        if len(describe_domain_resp.DomainList) == 0:
            raise AuthenticationError(
                f"Authenticate failed, domain {self.domain} not found"
            )
        self.domain_id = describe_domain_resp.DomainList[0].DomainId

    def cleanup(self) -> None:
        pass

    def create_record(self, rtype, name, content):
        create_record_req = models.CreateRecordRequest()
        params = {
            "Domain": self.domain,
            "SubDomain": self._relative_name(name),
            "RecordType": rtype,
            "RecordLine": "\u9ED8\u8BA4",
            "Value": content,
        }
        if self._get_lexicon_option("ttl"):
            params["TTL"] = self._get_lexicon_option("ttl")
        create_record_req.from_json_string(json.dumps(params))
        LOGGER.debug("create_record req: %s", create_record_req.to_json_string())
        create_record_resp = self.client.CreateRecord(create_record_req)
        LOGGER.debug("create_record resp: %s", create_record_resp.to_json_string())
        return True

    def list_records(self, rtype=None, name=None, content=None):
        list_record_req = models.DescribeRecordListRequest()
        params = {
            "Domain": self.domain,
        }
        if rtype is not None:
            params["Type"] = rtype
        if name is not None:
            params["Subdomain"] = self._relative_name(name)
        # qcloud dns api not support filter by content, implement it by client filter

        list_record_req.from_json_string(json.dumps(params))
        LOGGER.debug("list_records req: %s", list_record_req.to_json_string())
        list_record_resp = self.client.DescribeRecordList(list_record_req)
        LOGGER.debug("list_records resp: %s", list_record_resp.to_json_string())

        records = []
        for record in list_record_resp.RecordList:
            if content is not None and record.Value != content:
                continue
            records.append(
                {
                    "type": record.Type,
                    "name": self._full_name(record.Name),
                    "ttl": record.TTL,
                    "content": record.Value,
                    "id": record.RecordId,
                }
            )
        return records

    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        batch_delete_record_req = models.DeleteRecordBatchRequest()
        params = {}
        if not identifier:
            records = self.list_records(rtype, name, content)
            if len(records) == 0:
                return True
            params["RecordIdList"] = [record["id"] for record in records]
        else:
            params["RecordIdList"] = [identifier]
        batch_delete_record_req.from_json_string(json.dumps(params))

        LOGGER.debug("delete_record req: %s", batch_delete_record_req.to_json_string())
        batch_delete_record_resp = self.client.DeleteRecordBatch(
            batch_delete_record_req
        )
        LOGGER.debug(
            "delete_record resp: %s", batch_delete_record_resp.to_json_string()
        )
        return True

    def update_record(self, identifier, rtype=None, name=None, content=None):
        modify_record_req = models.ModifyRecordRequest()
        params = {
            "Domain": self.domain,
            "SubDomain": self._relative_name(name),
            "RecordType": rtype,
            "RecordLine": "\u9ED8\u8BA4",
            "Value": content,
            "RecordId": identifier,
        }
        if self._get_lexicon_option("ttl"):
            params["TTL"] = self._get_lexicon_option("ttl")

        modify_record_req.from_json_string(json.dumps(params))

        LOGGER.debug("update_record req: %s", modify_record_req.to_json_string())
        modify_record_resp = self.client.ModifyRecord(modify_record_req)
        LOGGER.debug("update_record resp: %s", modify_record_resp.to_json_string())

        return True
