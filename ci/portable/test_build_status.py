#!/usr/bin/env python3
"""Exercise the actual post-build shell gates without a compiler or HDL model."""
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# pylint: disable=missing-function-docstring

from collections import Counter
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(os.environ.get('BUILD_STATUS_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
MARKER = "# The harness uses this checkout's headers and release binary."
HEAD = '1' * 40
EVIDENCE = ('semantic-waves', 'finish-waves', 'controls-waves', 'sv-semantics-waves',
            'thread-waves', 'ram-waves', 'results')
REQUIRED = {
    'regress', 'check_results', 'threads', 'ram', 'git_head', 'icarus_run', 'icarus_check',
    'icarus_full18', 'finish9_run', 'finish9_check'
}
REQUIRED.update('evidence:' + mode for mode in EVIDENCE)


class BuildStatusTest(unittest.TestCase):
    """Keep independent shell gates running while preserving every failure."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.bin = self.folder / 'bin'
        self.bin.mkdir()
        (self.folder / 'lookup').mkdir()
        self.bash = shutil.which('bash')
        self.assertIsNotNone(self.bash)
        self.config = self.folder / 'config.json'
        self.trace = self.folder / 'trace.jsonl'
        self.source = (ROOT / 'ci/portable/build.bash').read_text(encoding='utf-8')
        self.assertEqual(self.source.count(MARKER), 1)
        self.tail = self.source.split(MARKER, 1)[1]
        tool = '#!' + sys.executable + '\n' + r'''
import json, os, sys
from pathlib import Path
config = json.loads(Path(os.environ['BUILD_STATUS_CONFIG']).read_text())
args = sys.argv[1:]
name = Path(sys.argv[0]).name
if name == 'git':
    key = 'git_head'
    if args != ['rev-parse', 'HEAD']:
        sys.exit(2)
else:
    program = Path(args[0]).name
    keys = {'run_regressions.py': 'regress', 'check_results.py': 'check_results',
            'run_thread_controls.py': 'threads', 'ram_acceptance.py': 'ram'}
    if program == 'log_evidence.py':
        key = 'evidence:' + args[1]
    elif program == 'icarus_acceptance.py':
        key = 'icarus_full18' if '--full18' in args else 'icarus_' + args[1]
    elif program == 'finish_acceptance.py':
        key = 'finish9_' + args[1]
    else:
        key = keys.get(program, 'unexpected:' + program)
with Path(config['trace']).open('a') as stream:
    stream.write(json.dumps({'key': key, 'args': args}) + '\n')
if key == config.get('missing'):
    # PATH lookup distinguishes a missing command from a nonexecutable file.
    os.execv(config['bash'], [config['bash'], '-c', 'PATH=$2; command "$1"',
                            'missing-test-tool', config['tool_name'], config['tool_path']])
if name == 'git':
    print(config['head'])
sys.exit(config['exits'].get(key, 2 if key.startswith('unexpected:') else 0))
'''
        for name in ('python3', 'git'):
            path = self.bin / name
            path.write_text(tool, encoding='utf-8')
            path.chmod(0o700)

    def run_tail(self, exits=None, smoke=0, smoke_record=0, missing=None, nonexecutable=False):
        if nonexecutable:
            (self.folder / 'lookup' / 'nonexecutable-tool').write_text('#!/bin/sh\nexit 0\n')
            self.assertFalse(os.access(self.folder / 'lookup' / 'nonexecutable-tool', os.X_OK))
        self.config.write_text(json.dumps({
            'trace': str(self.trace),
            'exits': exits or {},
            'head': HEAD,
            'missing': missing,
            'bash': self.bash,
            'tool_name': 'nonexecutable-tool' if nonexecutable else 'absent-tool',
            'tool_path': str(self.folder / 'lookup')
        }),
                               encoding='utf-8')
        self.trace.write_text('', encoding='utf-8')
        script = self.folder / 'gates.bash'
        script.write_text('set -euo pipefail\nroot=' + shlex.quote(str(self.folder)) +
                          '\nsmoke_status=' + str(smoke) + '\nsmoke_record_status=' +
                          str(smoke_record) + '\n' + self.tail,
                          encoding='utf-8')
        env = os.environ.copy()
        env.update(PATH=str(self.bin) + os.pathsep + env['PATH'],
                   BUILD_STATUS_CONFIG=str(self.config),
                   LC_ALL='C')
        env.pop('BASH_ENV', None)
        result = subprocess.run([self.bash, str(script)],
                                cwd=self.folder,
                                env=env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                check=False,
                                timeout=15)
        rows = [json.loads(line) for line in self.trace.read_text().splitlines()]
        keys = [row['key'] for row in rows]
        self.assertEqual(set(keys), REQUIRED, result.stdout + result.stderr)
        counts = Counter(keys)
        self.assertTrue(all(counts[key] == 1 for key in REQUIRED - {'evidence:results'}))
        self.assertEqual(keys[-1], 'evidence:results')
        for row in rows:
            if row['key'].startswith(('icarus_', 'finish9_')):
                args = row['args']
                self.assertEqual(args[args.index('--expected-head') + 1], HEAD)
        return result, rows

    def assert_failed(self, exits=None, **kwargs):
        result, rows = self.run_tail(exits, **kwargs)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('ORIGINAL_ACCEPTANCE_EXITS ', result.stdout)
        return result, rows

    def test_all_gates_succeed(self):
        result, _ = self.run_tail()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_final_results_emitted_once(self):
        result, rows = self.run_tail()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(sum(row['key'] == 'evidence:results' for row in rows), 1)

    def test_regression_failure_does_not_stop_acceptance(self):
        result, _ = self.assert_failed({'regress': 7, 'check_results': 1})
        self.assertIn('regress=7 regression_check=1', result.stdout)

    def test_regression_checker_failure_is_preserved(self):
        result, _ = self.assert_failed({'check_results': 9})
        self.assertIn('regression_check=9', result.stdout)

    def test_each_evidence_failure_is_preserved(self):
        for mode in EVIDENCE:
            with self.subTest(mode=mode):
                result, _ = self.assert_failed({'evidence:' + mode: 19})
                self.assertIn('mode=' + mode + ' shell_status=19', result.stdout)
                self.assertIn('evidence=1', result.stdout)

    def test_thread_failure_still_attempts_wave_and_acceptance(self):
        result, _ = self.assert_failed({'threads': 7, 'evidence:thread-waves': 2})
        self.assertIn('threads=7 ram_matrix=0', result.stdout)
        self.assertIn('mode=thread-waves shell_status=2', result.stdout)

    def test_ram_failure_still_attempts_wave_and_acceptance(self):
        result, _ = self.assert_failed({'ram': 9, 'evidence:ram-waves': 2})
        self.assertIn('threads=0 ram_matrix=9', result.stdout)
        self.assertIn('mode=ram-waves shell_status=2', result.stdout)

    def test_full18_run_failure_keeps_checkers_and_finish9(self):
        result, _ = self.assert_failed({'icarus_run': 3})
        self.assertIn('icarus18_run=3 applicable16_check=0 full18_check=0', result.stdout)

    def test_applicable16_failure_is_preserved(self):
        result, _ = self.assert_failed({'icarus_check': 1})
        self.assertIn('applicable16_check=1 full18_check=0', result.stdout)

    def test_full18_failure_cannot_be_masked_by_applicable16(self):
        result, _ = self.assert_failed({'icarus_full18': 1})
        self.assertIn('applicable16_check=0 full18_check=1', result.stdout)

    def test_finish9_run_failure_still_checks(self):
        result, _ = self.assert_failed({'finish9_run': 4})
        self.assertIn('finish9_run=4 finish9_check=0', result.stdout)

    def test_finish9_check_failure_is_preserved(self):
        result, _ = self.assert_failed({'finish9_check': 1})
        self.assertIn('finish9_run=0 finish9_check=1', result.stdout)

    def test_smoke_failures_do_not_stop_acceptance(self):
        for arguments in ({'smoke': 13}, {'smoke_record': 14}):
            with self.subTest(arguments=arguments):
                self.assert_failed(**arguments)

    def test_missing_tool_preserves_127_and_runs_later_gates(self):
        self.assertFalse((self.folder / 'lookup' / 'absent-tool').exists())
        self.assertFalse((self.folder / 'lookup' / 'absent-tool').is_symlink())
        result, _ = self.assert_failed(missing='evidence:semantic-waves')
        self.assertIn('mode=semantic-waves shell_status=127', result.stdout)
        self.assertIn('absent-tool', result.stderr)

    def test_nonexecutable_tool_preserves_126_and_runs_later_gates(self):
        result, _ = self.assert_failed(missing='evidence:semantic-waves', nonexecutable=True)
        self.assertIn('mode=semantic-waves shell_status=126', result.stdout)
        self.assertIn('nonexecutable-tool', result.stderr)

    def test_distinct_evidence_statuses_remain_visible(self):
        result, _ = self.assert_failed({
            'evidence:semantic-waves': 8,
            'evidence:finish-waves': 9,
            'evidence:results': 11
        })
        for mode, status in (('semantic-waves', 8), ('finish-waves', 9), ('results', 11)):
            self.assertIn('mode=' + mode + ' shell_status=' + str(status), result.stdout)


if __name__ == '__main__':
    unittest.main()
