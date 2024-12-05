from os.path import abspath, dirname, join

import toml

metadata = toml.load(join(dirname(dirname(abspath(__file__))), "pyproject.toml"))["project"]

master_doc = 'index'
project = "DNS-Lexicon"
version = release = metadata["version"]

extensions = [
    "sphinx_rtd_theme",
]

html_theme = "sphinx_rtd_theme"
