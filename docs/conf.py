from os.path import abspath, dirname, join

with open(join(dirname(dirname(abspath(__file__))), "VERSION"), encoding='utf-8') as version_file:
    version = version_file.read().strip()

master_doc = 'index'
project = "DNS-Lexicon"
release = version
