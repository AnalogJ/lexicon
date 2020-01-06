"""
Integration tests for EUserv provider

Author: Matthias Schoettle (@mschoettle), 2019
"""
import re
import json

from unittest import TestCase
from lexicon.tests.providers.integration_tests import IntegrationTests

# EUserv has a limit of 10 TXT entries. Therefore, the live recordings were
# and entries removed manually during the execution of the tests.
# Otherwise, a test case will fail with a corresponding error (maximum entries reached).

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class EUservProviderTests(TestCase, IntegrationTests):
    """Tests for EUserv"""
    provider_name = 'euserv'
    domain = 'schoettle.it'
    product_id_domain = 1

    def _filter_headers(self):
        return ['set-cookie']

    def _filter_query_parameters(self):
        return [
            ('password', 'PASSWORD'),
            ('email', 'EMAIL'),
            ('sess_id', 'SESSION_ID'),
            ('ord_no', 'ORDER_ID')]

    def _filter_response(self, response):
        for cookie in ['set-cookie', 'Set-Cookie']:
            if cookie in response['headers']:
                del response['headers'][cookie]

        if 'string' in response['body']:
            # Replace session and order id with placeholders
            response['body']['string'] = re.sub(
                br'"sess_id":{"value":"[\w.-]+"', b'"sess_id":{"value":"SESSION_ID"',
                response['body']['string'])

            response['body']['string'] = re.sub(
                br'"ord_no":{"value":"[\w.-]+"', b'"ord_no":{"value":"ORDER_ID"',
                response['body']['string'])

            # Replace orders in body with mock data (contains the minimal required data)
            filtered_body = json.loads(response['body']['string'].decode('UTF-8'))

            if 'result' in filtered_body and 'orders' in filtered_body['result']:
                filtered_body['result']['orders'] = [
                    {
                        'ord_no': {'value': 'ORDER_ID'},
                        'pg_id': {'value': self.product_id_domain},
                        'ord_description': {'value': 'Contract Name\n' + self.domain},
                    },
                ]

            response['body']['string'] = json.dumps(filtered_body).encode('UTF-8')

        return response
