#!/usr/bin/env python
# -*- coding: utf-8 -*-
import subprocess
import sys
import os
import shutil
import tempfile
import stat
import errno

from pylint import lint

REPO_DIR = os.path.dirname(os.path.dirname(__file__))

def get_pylint_upstream_master_note():
    sys.stdout.write('Prepare a temporary repository for upstream ...\n')
    worktree_dir = tempfile.mkdtemp()

    score = None

    try:
        subprocess.call('git clone --depth 1 https://github.com/AnalogJ/lexicon.git {0}'.format(worktree_dir))

        sys.stdout.write('Execute pylint on upstream master to calculate score diff ...\n')
        command = '{0} -c "import sys; from pylint.lint import Run; results = Run([\'lexicon\', \'tests\'], do_exit=False); sys.stdout.write(str(results.linter.stats[\'global_note\']));"'.format(sys.executable)
        stdout = subprocess.check_output(command, shell=True, cwd=worktree_dir, universal_newlines=True)
        score = float(stdout.strip().split('\n')[-1])
    finally:
        def del_rw(action, name, exc):
            os.chmod(name, stat.S_IWRITE)
            os.remove(name)
        shutil.rmtree(worktree_dir, ignore_errors=False, onerror=del_rw)

    return score

def quality_gate(stats, upstream_master_note):
    quality_errors = []
    
    print(stats['global_note'])
    print(upstream_master_note)
    if stats['fatal']:
        quality_errors.append('Quality gate failure: {0} "fatal" issues have been found.\n'.format(stats['fatal']))

    if stats['error']:
        quality_errors.append('Quality gate failure: {0} "error" issues have been found.\n'.format(stats['error']))

    if stats['global_note'] < upstream_master_note:
        quality_errors.append('Quality gate failure: pylint global note is decreasing compared to master: {0} => {1}\n'.format(upstream_master_note, stats['global_note']))

    if quality_errors:
        for quality_error in quality_errors:
            sys.stderr.write(quality_error)
        return 1
    
    return 0

def main():
    upstream_master_note = get_pylint_upstream_master_note()

    sys.stdout.write('Execute pylint on current branch ...\n')
    results = lint.Run([os.path.join(REPO_DIR, 'lexicon'), os.path.join(REPO_DIR, 'tests'), '--persistent=n'], do_exit=False)

    stats = results.linter.stats
    sys.exit(quality_gate(stats, upstream_master_note))

if __name__ == '__main__':
    main()
