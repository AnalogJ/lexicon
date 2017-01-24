# How to contribute

Thanks! There are tons of different DNS services, and unfortunately a large
portion of them require paid accounts, which makes it hard for us to develop
`lexicon` providers on our own. We want to keep it as easy as possible to
contribute to `lexicon`, so that you can use your favorite DNS service with
your app. There are a few guidelines that we
need contributors to follow so that we can have a chance of keeping on
top of things.

## Things you should know

Before you jump in and write a provider, please keep in mind the following:

- `lexicon` is designed to work with multiple versions of python. That means
your code will be tested against python 2.7, 3.4, 3.5
- your provider should run (and pass) the integration test suite (we'll show
you how to set it up below)
- any provider specific dependenices should be added to the `setup.py` file,
 under the `extra_requires` heading. The group name should be the name of the
 provider. eg:

 	    extras_require={
            'route53': ['boto3']
        }

## Getting Started

Fork, then clone the repo:

    git clone git@github.com:your-username/lexicon.git

Install all `lexicon` requirements:

	pip install -r optional-requirements.txt
	pip install -r test-requirements.txt

Install `lexicon` in development mode

	python setup.py develop

Make sure the tests pass:

    py.test tests


## Adding a new DNS provider

Now that you have a working development environment, lets add a new provider.
Internally lexicon does a bit of magic to wire everything together, so the only
thing you'll really need to do is is create the following file.

 - `lexicon/providers/foo.py`

Where `foo` should be replaced with the name of the DNS service in lowercase
and without spaces or special characters (eg. `cloudflare`)

Your provider file should contain 2 things:

- a `ProviderParser` which is used to add provider specific commandline arguments.
eg. If you define two cli arguments: `--auth-username` and `--auth-token`,
 those values will be available to your provider via `self.options['auth_username']`
 or `self.options['auth_token']` respectively

- a `Provider` class which inherits from [`BaseProvider`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py), which is in the `base.py` file.
The [`BaseProvider`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/base.py)
defines the following functions, which must be overridden in your provider implementation:

	- `authenticate`
    - `create_record`
    - `list_records`
    - `update_record`
    - `delete_record`
    - `_request`

	It also provides a few helper functions which you can use to simplify your implemenation.
	See the [`cloudflare.py`](https://github.com/AnalogJ/lexicon/blob/master/lexicon/providers/cloudflare.py)
	 file, or any provider in the [`lexicon/providers/`](https://github.com/AnalogJ/lexicon/tree/master/lexicon/providers) folder for examples


	from __future__ import print_function
    from __future__ import absolute_import
    from .base import Provider as BaseProvider

## Testing your provider

First let's validate that your provider shows up in the CLI

	lexicon foo --help

If everything worked correctly, you should get a help page that's specific
to your provider, including your custom optional arguments.

Now you can run some manual commands against your provider to verify that
everything works as you expect.

	lexicon foo list example.com TXT
	lexicon foo create example.com TXT --name demo --content "fake content"

Once you're satisfied that your provider is working correctly, we'll run the
integration test suite against it, and verify that your provider responds the
same as all other `lexicon` providers. `lexicon` uses `vcrpy` to make recordings
 of actual HTTP requests against your DNS service's API, and then reuses those
 recordings during testing.

The only thing you need to do is create the following file:

 - `tests/providers/test_foo.py`

Then you'll need to populate it with the following template:

	# Test for one implementation of the interface
    from lexicon.providers.foo import Provider
    from integration_tests import IntegrationTests
    from unittest import TestCase
    import pytest

    # Hook into testing framework by inheriting unittest.TestCase and reuse
    # the tests which *each and every* implementation of the interface must
    # pass, by inheritance from define_tests.TheTests
    class FooProviderTests(TestCase, IntegrationTests):

        Provider = Provider
        provider_name = 'foo'
        domain = 'example.com'
        def _filter_post_data_parameters(self):
            return ['login_token']

		def _filter_headers(self):
			return ['Authorization']

		def _filter_query_parameters(self):
			return ['secret_key']

Make sure to replace any instance of `foo` or `Foo` with your provider name.
`domain` should be a real domain registered with your provider (some
providers don't require you to validate ownership).

The `_filter_*` methods ensure that your credentials are not included in the
`vcrpy` recordings that are created. You can take a look at recordings for other
 providers, they are stored in the [`tests/fixtures/cassettes/`](https://github.com/AnalogJ/lexicon/tree/master/tests/fixtures/cassettes) sub-folders.

Then you'll need to setup your environment variables for testing. Unlike running
`lexicon` via the CLI, the test suite cannot take user input, so we'll need to provide
any `auth-*` arguments using environmental variables prefixed with `LEXICON_`.

eg. if you had a `--auth-token` CLI argument, you can also populate it
using the `LEXICON_AUTH_TOKEN` environmental variable.

Now run the `py.test` suite again. It will automatically generate recordings for
your provider:

	py.test tests/providers/test_foo.py

If any of the integration tests fail on your provider, you'll need to delete the recordings that were created,
make your changes and then try again.

	rm -rf tests/fixtures/cassettes/foo/IntegrationTests

Once all your tests pass, you'll want to double check that there is no sensitive data in the
`tests/fixtures/cassettes/foo/IntegrationTests` folder, and then `git add` the whole folder.

	git add tests/fixtures/cassettes/foo/IntegrationTests

Finally, push your changes to your Github fork, and open a PR.

:)
