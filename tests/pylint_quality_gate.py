#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil
import tempfile
import contextlib
import stat
from io import StringIO

from pylint import lint


REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@contextlib.contextmanager
def capture():
    oldout, olderr = sys.stdout, sys.stderr
    try:
        out = [StringIO(), StringIO()]
        sys.stdout, sys.stderr = out
        yield out
    finally:
        sys.stdout, sys.stderr = oldout, olderr
        out[0] = out[0].getvalue()
        out[1] = out[1].getvalue()


def get_pylint_upstream_master_note():
    """
    Get the pylint global note of lexicon on upstream master branch
    """
    sys.stdout.write(
        '===> Preparing a temporary local repository for upstream ... <===\n')
    worktree_dir = tempfile.mkdtemp()

    try:
        sys.stdout.write('===> Executing pylint on upstream master '
                         'to calculate pylint global note diff ... <===\n')

        subprocess.check_output([
            'git', 'clone', '--depth=1', 'https://github.com/AnalogJ/lexicon.git',
            worktree_dir], stderr=subprocess.STDOUT)
        subprocess.check_output(['pip', 'install', '-e', worktree_dir], stderr=subprocess.STDOUT)
        with capture():
            results = lint.Run([
                os.path.join(worktree_dir, 'lexicon'), os.path.join(worktree_dir, 'tests'),
                os.path.join(worktree_dir, 'tests', 'providers'), '--persistent=n'],
                do_exit=False)

        return results.linter.stats['global_note']
    finally:
        def del_rw(_, name, __):
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
        shutil.rmtree(worktree_dir, onerror=del_rw)


def quality_gate(stats, upstream_master_note):
    """
    Trigger various performance metrics on code quality.
    Raise if these metrics do not match expectations.
    """
    quality_errors = []

    sys.stdout.write('=====================\n')
    sys.stdout.write('Quality gate results:\n')
    sys.stdout.write('=====================\n')

    if stats['fatal']:
        quality_errors.append('Quality gate failure: {0} "fatal" issues have been found.\n'
                              .format(stats['fatal']))

    if stats['error']:
        quality_errors.append('Quality gate failure: {0} "error" issues have been found.\n'
                              .format(stats['error']))

    if stats['global_note'] < upstream_master_note:
        quality_errors.append('Quality gate failure: pylint global note is '
                              'decreasing compared to master: {0} => {1}\n'
                              .format(upstream_master_note, stats['global_note']))
    else:
        sys.stdout.write('Info: pylint global is increasing or stable compared to master: '
                         '{0} => {1}\n'.format(upstream_master_note, stats['global_note']))

    if quality_errors:
        for quality_error in quality_errors:
            sys.stderr.write(quality_error)
        return 1

    return 0


def main():
    """Main process"""
    upstream_master_note = get_pylint_upstream_master_note()

    # Script is located two levels deep in the repository root (./tests/pylint_quality_gate.py)
    repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    sys.stdout.write('===> Executing pylint on current branch ... <===\n')
    subprocess.check_output(['pip', 'install', '-e', repo_dir], stderr=subprocess.STDOUT)
    results = lint.Run([
        os.path.join(repo_dir, 'lexicon'), os.path.join(repo_dir, 'tests'),
        os.path.join(repo_dir, 'tests', 'providers'), '--persistent=n'],
        do_exit=False)

    stats = results.linter.stats
    sys.exit(quality_gate(stats, upstream_master_note))


if __name__ == '__main__':
    main()
