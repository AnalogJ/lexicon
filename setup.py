"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path, listdir

version = 'unknown'
with open(path.join(path.dirname(path.abspath(__file__)), 'VERSION'), encoding='utf-8') as version_file:
    version = version_file.read().strip()

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# Get a list of all the providers
current_filepath = path.join(here, 'lexicon', 'providers')
providers = [path.splitext(f)[0] for f in listdir(current_filepath) if path.isfile(path.join(current_filepath, f))]
providers = list(sorted(set(providers)))
providers.remove('base')
providers.remove('__init__')

# Define optional dependencies for specific providers.
# Each key of the dict should match a provider name.
extras_require = {
    'namecheap': ['PyNamecheap'],
    'route53': ['boto3'],
    'softlayer': ['SoftLayer'],
    'subreg': ['zeep'],
    'transip': ['transip>=0.3.0'],
    'plesk': ['xmltodict'],
    'henet': ['beautifulsoup4'],
    'hetzner': ['dnspython>=1.15.0','beautifulsoup4'],
    'easyname': ['beautifulsoup4'],
    'localzone': ['localzone'],
}

# Add a 'full' extra, gathering all external dependencies for providers
extras_require['full'] = set([dep for deps in extras_require.values() for dep in deps])

# Define dev/test dependencies
extras_require['dev'] = [
    'pytest==4.1.1',
    'pytest-cov==2.6.1',
    'pytest-xdist==1.26.1',
    'python-coveralls==2.9.1',
    'vcrpy==2.0.1',
    'mock==2.0.0',
]

setup(
    name='dns-lexicon',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version=version,

    description='Manipulate DNS records on various DNS providers in a standardized/agnostic way',
    long_description=long_description,
    long_description_content_type="text/markdown",

    # The project's main homepage.
    url='https://github.com/AnalogJ/lexicon',

    # Author details
    author='Jason Kulatunga',
    author_email='jason@thesparktree.com',

    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Internet :: Name Service (DNS)',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',

        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],

    keywords='dns lexicon dns-lexicon dehydrated letsencrypt ' + ' '.join(providers),

    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=[
        'requests[security]',
        'tldextract',
        'future',
        'cryptography',
        'pyyaml',
    ],

    extras_require=extras_require,

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'lexicon=lexicon.cli:main',
        ],
    },
    test_suite='tests'
)
