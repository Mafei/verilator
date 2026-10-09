#!/usr/bin/env python3
"""Exercise Python lint failure propagation without running a compiler."""
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# pylint: disable=missing-function-docstring

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(os.environ.get('LINT_STATUS_SOURCE_ROOT', Path(__file__).resolve().parents[2]))
ERROR = "fixture.py:1:0: E0602: Undefined variable 'test' (undefined-variable)\n"
WARNING = "fixture.py:2:0: W0611: Unused import vltest_bootstrap (unused-import)\n"
UNEXPECTED = "fixture.py:3:0: E0606: Possibly using variable 'dumper' before assignment\n"


class LintStatusTest(unittest.TestCase):
    """Check the actual Make recipes with successful and failing tools."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        (self.folder / 'nodist').mkdir()
        shutil.copyfile(ROOT / 'nodist/lint_py_test_filter',
                        self.folder / 'nodist/lint_py_test_filter')
        self.makefile = (ROOT / 'Makefile.in').read_text(encoding='utf-8')
        self.tool = self.folder / 'fake_tool.py'
        self.tool.write_text('''import json,os,signal,sys
from pathlib import Path
config=json.loads(Path(sys.argv[1]).read_text())
if 'fail_file' in config:
    name=Path(sys.argv[-1]).name
    with Path(config['trace']).open('a') as output:
        output.write(name+'\\n')
    sys.exit(1 if name==config['fail_file'] else 0)
sys.stdout.write(config['stdout'])
sys.stdout.flush()
sys.stderr.write(config.get('stderr',''))
if config['exit']<0:
    os.kill(os.getpid(),signal.SIGTERM)
sys.exit(config['exit'])
''',
                             encoding='utf-8')

    def run_target(self, target, definitions):
        recipe = self.makefile.split(target + ':\n', 1)[1].split('\n\n', 1)[0]
        source = self.folder / 'fixture.mk'
        source.write_text(definitions + '\n' + target + ':\n' + recipe + '\n', encoding='utf-8')
        return subprocess.run(['make', '-s', '-f', str(source), target],
                              cwd=self.folder,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              check=False)

    def pylint(self, status, output='', error=''):
        config = self.folder / 'pylint.json'
        config.write_text(json.dumps({
            'exit': status,
            'stdout': output,
            'stderr': error
        }),
                          encoding='utf-8')
        definitions = ('PYTHON3 = ' + sys.executable + '\nPYLINT = ' + sys.executable + ' ' +
                       str(self.tool) + ' ' + str(config) +
                       '\nPYLINT_TEST_FLAGS =\nPY_TEST_FILES =')
        return self.run_target('lint-py-pylint-tests', definitions)

    def test_mypy_keeps_failures_and_checks_all_files(self):
        for fail_file in ['first.py', 'middle.py', 'last.py', 'none']:
            with self.subTest(fail_file=fail_file):
                files = [self.folder / name for name in ['first.py', 'middle.py', 'last.py']]
                for filename in files:
                    filename.write_text('# mypy\n', encoding='utf-8')
                trace = self.folder / 'trace'
                trace.write_text('', encoding='utf-8')
                config = self.folder / 'mypy.json'
                config.write_text(json.dumps({
                    'fail_file': fail_file,
                    'trace': str(trace)
                }),
                                  encoding='utf-8')
                definitions = ('MYPY = ' + sys.executable + ' ' + str(self.tool) + ' ' +
                               str(config) + '\nMYPY_FLAGS =\nPY_PROGRAMS = ' +
                               ' '.join(str(filename) for filename in files))
                result = self.run_target('lint-py-mypy', definitions)
                self.assertEqual(result.returncode == 0, fail_file == 'none')
                self.assertEqual(trace.read_text().splitlines(),
                                 ['first.py', 'middle.py', 'last.py'])

    def test_empty_success(self):
        self.assertEqual(self.pylint(0).returncode, 0)

    def test_expected_suppressions(self):
        for status, output in [(2, ERROR), (4, WARNING), (6, ERROR + WARNING)]:
            with self.subTest(status=status):
                result = self.pylint(status, '************* Module fixture\n' + output)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, b'')

    def test_fatal_usage_signal_and_empty_nonzero(self):
        for status in [1, 2, 4, 6, 8, 16, 32, -15]:
            with self.subTest(status=status):
                self.assertNotEqual(self.pylint(status).returncode, 0)

    def test_fatal_cannot_hide_behind_suppressed_errors(self):
        self.assertNotEqual(self.pylint(3, ERROR).returncode, 0)

    def test_headers_and_substrings_cannot_explain_nonzero_exit(self):
        self.assertNotEqual(self.pylint(6, '************* Module fixture\n').returncode, 0)
        self.assertNotEqual(self.pylint(2, ERROR.split(': ', 1)[1]).returncode, 0)

    def test_status_must_match_suppressed_diagnostics(self):
        self.assertNotEqual(self.pylint(6, ERROR).returncode, 0)
        self.assertNotEqual(self.pylint(0, ERROR).returncode, 0)

    def test_unexpected_output_fails(self):
        for status in [0, 2, 6]:
            with self.subTest(status=status):
                result = self.pylint(status, ERROR + WARNING + UNEXPECTED)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout.decode(), UNEXPECTED)

    def test_stderr_is_preserved(self):
        result = self.pylint(32, error='fixture usage error\n')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b'fixture usage error\n', result.stdout + result.stderr)

    def test_stderr_cannot_hide_behind_success_or_suppressed_errors(self):
        for status, output in [(0, ''), (2, ERROR)]:
            with self.subTest(status=status):
                result = self.pylint(status, output, 'fixture unexpected stderr diagnostic\n')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'fixture unexpected stderr diagnostic\n', result.stdout)

    def test_legacy_stdin_output(self):
        command = [sys.executable, str(ROOT / 'nodist/lint_py_test_filter')]
        for text, expected_status, expected_output in [
            ('************* Module fixture\n' + ERROR + WARNING, 0, ''),
            (ERROR + UNEXPECTED, 1, UNEXPECTED)
        ]:
            with self.subTest(expected_status=expected_status):
                result = subprocess.run(command,
                                        input=text.encode(),
                                        stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,
                                        check=False)
                self.assertEqual(result.returncode, expected_status)
                self.assertEqual(result.stdout.decode(), expected_output)


if __name__ == '__main__':
    unittest.main()
