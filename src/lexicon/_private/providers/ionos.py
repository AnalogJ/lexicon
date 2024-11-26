import requests

from lexicon.interfaces import Provider as BaseProvider


_ZONES_API = 'https://api.hosting.ionos.com/dns/v1/zones'


class Provider(BaseProvider):

    @staticmethod
    def get_nameservers():
        return ['ui-dns.com', 'ui-dns.org', 'ui-dns.de', 'ui-dns.biz']

    @staticmethod
    def configure_parser(parser):
        parser.add_argument(
            '--api-key',
            required=True,
            help='IONOS api key: public prefix + period + key proper',
        )

    def authenticate(self):
        zones = self._get(_ZONES_API)
        for zone in zones:
            if zone['name'] == self.domain:
                self.domain_id = zone['id']

    def create_record(self, rtype, name, content):
        raise NotImplementedError()

    def list_records(self, rtype=None, name=None, content=None):
        query_params = {}
        if rtype:
            query_params['recordType'] = rtype
        if name:
            query_params['recordName'] = name
        data = self._get(_ZONES_API + '/' + self.domain_id, query_params)
        records = data['records']
        records = [{
            'type': r['type'],
            'name': r['name'],
            'ttl': r['ttl'],
            'content': r['content'],
            'id': r['id'],
        } for r in records]
        for record in records:
            self._clean_TXT_record(record)
        if content:
            records = [r for r in records if r['content'] == content]
        return records

    def update_record(self, identifier, rtype, name, content):
        raise NotImplementedError()

    def delete_record(self, identifier, rtype, name, content):
        raise NotImplementedError()

    def _request(self, action='GET', url='/', data=None, query_params=None):
        response = requests.request(
            action,
            url,
            params=query_params,
            json=data,
            headers={
                'accept': 'application/json',
                'x-api-key': self._get_provider_option('api_key'),
            },
        )
        response.raise_for_status()
        return response.json()
