import requests

from lexicon.interfaces import Provider as BaseProvider

_ZONES_API = "https://api.hosting.ionos.com/dns/v1/zones"


class Provider(BaseProvider):

    @staticmethod
    def get_nameservers():
        return ["ui-dns.com", "ui-dns.org", "ui-dns.de", "ui-dns.biz"]

    @staticmethod
    def configure_parser(parser):
        parser.add_argument(
            "--api-key",
            required=True,
            help="IONOS api key: public prefix + period + key proper",
        )

    def authenticate(self):
        zones = self._get(_ZONES_API)
        for zone in zones:
            if zone["name"] == self.domain:
                self.domain_id = zone["id"]
                return
        raise Exception("domain not found: " + self.domain)

    def create_record(self, rtype, name, content):
        self._post(
            _ZONES_API + "/" + self.domain_id + "/records",
            data=[
                {
                    "name": self._full_name(name),
                    "type": rtype,
                    "content": content,
                    "ttl": self._get_lexicon_option("ttl"),
                    "prio": 0,
                    "disabled": False,
                }
            ],
        )
        return True

    def list_records(self, rtype=None, name=None, content=None):
        query_params = {}
        if rtype:
            query_params["recordType"] = rtype
        if name:
            query_params["recordName"] = self._full_name(name)
        data = self._get(_ZONES_API + "/" + self.domain_id, query_params)
        records = data["records"]
        records = [
            {
                "type": r["type"],
                "name": r["name"],
                "ttl": r["ttl"],
                "content": r["content"],
                "id": r["id"],
            }
            for r in records
        ]
        for record in records:
            self._clean_TXT_record(record)
        if content:
            records = [r for r in records if r["content"] == content]
        return records

    def update_record(self, identifier, rtype, name, content):
        self.delete_record(identifier, rtype, name, None)
        return self.create_record(rtype, name, content)

    def delete_record(self, identifier=None, rtype=None, name=None, content=None):
        if identifier:
            identifiers = [identifier]
        else:
            identifiers = [r["id"] for r in self.list_records(rtype, name, content)]
        for identifier in identifiers:
            self._delete(_ZONES_API + "/" + self.domain_id + "/records/" + identifier)
        return True

    def _request(self, action="GET", url="/", data=None, query_params=None):
        response = requests.request(
            action,
            url,
            params=query_params,
            json=data,
            headers={
                "accept": "application/json",
                "x-api-key": self._get_provider_option("api_key"),
            },
        )
        response.raise_for_status()
        try:
            return response.json()
        except requests.exceptions.JSONDecodeError:
            return True
