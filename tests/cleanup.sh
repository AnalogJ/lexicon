PROVIDER_NAME=rage4
TEST_DOMAIN=capsulecd.com
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.createrecordset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.deleterecordinset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.deleterecordset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.fqdn.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.full.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.listrecordset.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.noop.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name _acme-challenge.test.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name random.fqdntest.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name random.fulltest.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name random.test.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name updated.test.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name updated.testfqdn.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name updated.testfull.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com A --name localhost.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com TXT --name ttl.fqdn.${TEST_DOMAIN}
lexicon ${PROVIDER_NAME} delete capsulecd.com CNAME --name docs.${TEST_DOMAIN}
