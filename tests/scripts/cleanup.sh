#!/bin/sh
PROVIDER_NAME=rage4
TEST_DOMAIN=example.com
#AUTH="--auth-token=XXX"
echo "Cleaning up domain ${TEST_DOMAIN} in ${PROVIDER_NAME}"
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.createrecordset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.deleterecordinset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.deleterecordset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.fqdn.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.full.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.listrecordset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.noop.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name _acme-challenge.test.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name random.fqdntest.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name random.fulltest.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name random.test.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name updated.test.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name updated.testfqdn.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name updated.testfull.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name orig.nameonly.test.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} A     ${AUTH} --name localhost.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} TXT   ${AUTH} --name ttl.fqdn.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete ${TEST_DOMAIN} CNAME ${AUTH} --name docs.${TEST_DOMAIN}
