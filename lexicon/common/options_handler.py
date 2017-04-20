import os

# make sure that auth parameters can be specified via environmental variables as well.
# basically we map env variables for the chosen provider to the options dictionary (if a value isnt already provided)
# LEXICON_CLOUDFLARE_TOKEN => options['auth_token']
# LEXICON_CLOUDFLARE_USERNAME => options['auth_username']
# LEXICON_CLOUDFLARE_PASSWORD => options['auth_password']
# we only care about environmental variables for this Provider, which match --auth-* CLI parameters.
def env_auth_options(provider_name):
    options = {}

    env_prefix = 'LEXICON_{0}_'.format(provider_name.upper())
    for key in list(os.environ.keys()):
        if key.startswith(env_prefix):
            auth_type = key[len(env_prefix):].lower()
            options['auth_{0}'.format(auth_type)] = os.environ[key]
    return SafeOptions(options)


class SafeOptions(dict):
    def update(self, update_options):
        if update_options:
            super(SafeOptions, self).update({k:v for k,v in update_options.items() if v})


class SafeOptionsWithFallback(SafeOptions):
    def __init__(self, content=None, fallbackFn=None):
        super(SafeOptionsWithFallback, self).__init__()
        self.update(content)
        self.fallbackFn = fallbackFn or (lambda x: None)

    #this method is the exact same as __main__.py parse env, with some slight modifications to storage.
    # should not be used directly.
    def __missing__(self, key):
        return self.fallbackFn(key)

    def get(self,key,default=None):
        return self[key] or default
