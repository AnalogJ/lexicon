#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from pylint import lint


REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOBAL_NOTE_THRESHOLD = 8.12


def quality_gate(stats):
    """
    Trigger various performance metrics on code quality.
    Raise if these metrics do not match expectations.
    """
    quality_errors = False

    sys.stdout.write('=====================\n')
    sys.stdout.write('Quality gate results:\n')
    sys.stdout.write('=====================\n')

    if stats['fatal']:
        sys.stderr.write('1) Failure: {0} "fatal" issues have been found.\n'
                         .format(stats['fatal']))
        quality_errors = True
    else:
        sys.stdout.write('1) OK: No "fatal" issues have been found.\n')

    if stats['error']:
        sys.stderr.write('2) Failure: {0} "error" issues have been found.\n'
                         .format(stats['error']))
        quality_errors = True
    else:
        sys.stdout.write('2) OK. No "error" issues have been found.\n')

    if stats['global_note'] < GLOBAL_NOTE_THRESHOLD:
        sys.stderr.write('3) Failure: pylint global note is below threshold: {0} < {1}\n'
                         .format(stats['global_note'], GLOBAL_NOTE_THRESHOLD))
        quality_errors = True
    else:
        sys.stdout.write('3) OK: pylint global note is beyond threshold: {0} >= {1}\n'
                         .format(stats['global_note'], GLOBAL_NOTE_THRESHOLD))

    return 0 if not quality_errors else 1


def main():
    """Main process"""
    # Script is located two levels deep in the repository root (./tests/pylint_quality_gate.py)
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    sys.stdout.write('===> Executing pylint ... <===\n')
    results = lint.Run([
        os.path.join(repo_dir, 'lexicon'),
        os.path.join(repo_dir, 'tests'),
        os.path.join(repo_dir, 'tests', 'providers'), '--persistent=n'],
        do_exit=False)

    stats = results.linter.stats
    sys.exit(quality_gate(stats))


if __name__ == '__main__':
    main()
