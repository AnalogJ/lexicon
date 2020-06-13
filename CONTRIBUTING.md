# How to contribute

Thanks! There are tons of different DNS services, and unfortunately a large
portion of them require paid accounts, which makes it hard for us to develop
`lexicon` providers on our own. We want to keep it as easy as possible to
contribute to `lexicon`, so that you can automate your favorite DNS service.
There are a few guidelines that we need contributors to follow so that 
we can keep on top of things.

## Getting Started

Fork, then clone the repo:

    $ git clone git@github.com:your-username/lexicon.git

Create a python virtual environment:

	$ virtualenv -p python2.7 venv
	$ source venv/bin/activate

Install `lexicon` in development mode with full providers support:

    $ pip install -e .[full,dev]

Make sure the tests pass:

    $ py.test lexicon/tests

You can test a specific provider using:

	$ py.test lexicon/tests/providers/test_foo.py

_NB: Please note that by default, tests are replayed from recordings located in `tests/fixtures/cassettes`, not against the real DNS provider APIs._

## Adding a new DNS provider

Now that you have a working development environment, lets add a new provider.
Internally lexicon does a bit of magic to wire everything together, so the only
thing you'll really need to do is is create the following file.

 - `lexicon/providers/foo.py`

Where `foo` should be replaced with the name of the DNS service in lowercase
and without spaces or special characters (eg. `cloudflare`)

Your provider file should contain 3 things:

- a `NAMESERVER_DOMAINS` which contains the domain(s) used by the DNS provider nameservers FQDNs
(eg. Google Cloud DNS uses nameservers that have the FQDN pattern `ns-cloud-cX-googledomains.com`,
so `NAMESERVER_DOMAINS` will be `['googledomains.com']`).

- a `provider_parser` which is used to add provider specific commandline arguments.
eg. If you define two cli arguments: `--auth-username` and `--auth-token`,
 those values will be available to your provider via `self._get_provider_option('auth_username')`
 or `self._get_provider_option('auth_token')` respectively

- a `Provider` class which inherits from [`BaseProvider`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py), which is in the `base.py` file.
The [`BaseProvider`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py)
defines the following functions, which must be overridden in your provider implementation:

    - `_authenticate`
    - `_create_record`
    - `_list_records`
    - `_update_record`
    - `_delete_record`
    - `_request`

	It also provides a few helper functions which you can use to simplify your implemenation.
	See the [`cloudflare.py`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/cloudflare.py)
	 file, or any provider in the [`lexicon/providers/`](https://github.com/AnalogJ/lexicon/tree/master/lexicon/providers) folder for examples

It's a good idea to review the provider [specification](https://github.com/AnalogJ/lexicon/blob/master/SPECIFICATION.md) to ensure that your interface follows
the proper conventions.


## Testing your provider

First let's validate that your provider shows up in the CLI

	$ lexicon foo --help

If everything worked correctly, you should get a help page that's specific
to your provider, including your custom optional arguments.

Now you can run some manual commands against your provider to verify that
everything works as you expect.

	$ lexicon foo list example.com TXT
	$ lexicon foo create example.com TXT --name demo --content "fake content"

Once you're satisfied that your provider is working correctly, we'll run the
integration test suite against it, and verify that your provider responds the
same as all other `lexicon` providers. `lexicon` uses `vcrpy` to make recordings
 of actual HTTP requests against your DNS service's API, and then reuses those
 recordings during testing.

The only thing you need to do is create the following file:

 - `lexicon/tests/providers/test_foo.py`

Then you'll need to populate it with the following template:

```python
# Test for one implementation of the interface
from lexicon.tests.providers.integration_tests import IntegrationTestsV2
from unittest import TestCase

# Hook into testing framework by inheriting unittest.TestCase and reuse
# the tests which *each and every* implementation of the interface must
# pass, by inheritance from integration_tests.IntegrationTests
class FooProviderTests(TestCase, IntegrationTestsV2):
    """Integration tests for Foo provider"""
	provider_name = 'foo'
	domain = 'example.com'
	def _filter_post_data_parameters(self):
		return ['login_token']

	def _filter_headers(self):
		return ['Authorization']

	def _filter_query_parameters(self):
		return ['secret_key']

	def _filter_response(self, response):
		"""See `IntegrationTests._filter_response` for more information on how
		to filter the provider response."""
		return response
```

Make sure to replace any instance of `foo` or `Foo` with your provider name.
`domain` should be a real domain registered with your provider (some
providers have a sandbox/test environment which doesn't require you to validate ownership).

The `_filter_*` methods ensure that your credentials are not included in the
`vcrpy` recordings that are created. You can take a look at recordings for other
 providers, they are stored in the [`tests/fixtures/cassettes/`](https://github.com/AnalogJ/lexicon/tree/master/tests/fixtures/cassettes) sub-folders.

Then you'll need to setup your environment variables for testing. Unlike running
`lexicon` via the CLI, the test suite cannot take user input, so we'll need to provide
any CLI arguments containing secrets (like `--auth-*`) using environmental variables prefixed
with `LEXICON_FOO_`.

For instance, if you had a `--auth-token` CLI argument, you can populate it
using the `LEXICON_FOO_AUTH_TOKEN` environmental variable.

Notice also that you should pass any required non-secrets arguments programmatically using the `_test_parameters_override()` method. See
https://github.com/AnalogJ/lexicon/blob/5ee4d16f9d6206e212c2197f2e53a1db248f5eb9/lexicon/tests/providers/test_powerdns.py#L19
for an example.

## Test recordings

Now you need to run the `py.test` suite again, but in a different mode: the live tests mode. 
In default test mode, tests are replayed from existing recordings. In live mode, tests are executed against the real DNS provider API, and recordings will automatically be generated for your provider.

To execute the `py.test` suite using the live tests mode, execute py.test with the environment variable `LEXICON_LIVE_TESTS` set to `true` like below:

	LEXICON_LIVE_TESTS=true py.test lexicon/tests/providers/test_foo.py

If any of the integration tests fail on your provider, you'll need to delete the recordings that were created,
make your changes and then try again.

	rm -rf tests/fixtures/cassettes/foo/IntegrationTests

Once all your tests pass, you'll want to double check that there is no sensitive data in the
`tests/fixtures/cassettes/foo/IntegrationTests` folder, and then `git add` the whole folder.

	git add tests/fixtures/cassettes/foo/IntegrationTests

Finally, push your changes to your Github fork, and open a PR.

:)

## Skipping Tests/Suites

Neither of the snippets below should be used unless necessary. They are only included in the interest of documentation.

In your `lexicon/tests/providers/test_foo.py` file, you can use `@pytest.mark.skip` to skip any individual test that does not apply (and will never pass)

```python
	@pytest.mark.skip(reason="can not set ttl when creating/updating records")
	def test_provider_when_calling_list_records_after_setting_ttl(self):
		return
```

You can also skip extended test suites by inheriting your provider test class from ``IntegrationTestsV1`` instead of ``IntegrationTestsV2``:

```python
from lexicon.tests.providers.integration_tests import IntegrationTestsV1
from unittest import TestCase

class FooProviderTests(TestCase, IntegrationTestsV1):
    """Integration tests for Foo provider"""
```

## CODEOWNERS file

Next, you should add yourself to the [CODEOWNERS file](https://github.com/AnalogJ/lexicon/blob/master/CODEOWNERS), in the root of the repo. It's my way of keeping track of who to ping when I need updated recordings as the test suites expand & change.

## Additional Notes

Please keep in mind the following:

- `lexicon` is designed to work with multiple versions of python. That means
your code will be tested against python 2.7, 3.5, 3.6 and 3.7
- any provider specific dependenices should be added to the `setup.py` file,
 under the `extra_requires` heading. The group name should be the name of the
 provider. eg:

 	    extras_require={
            'route53': ['boto3']
        }

 when adding a new group, make sure it has been added to the `optional-requirements.txt` file as well.
