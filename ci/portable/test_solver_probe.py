#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Check real child waits and protocol bytes when the runtime kills its launcher."""
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROBE = Path(__file__).with_name('solver_probe.py')


class SolverProbeTest(unittest.TestCase):
    """Exercise the actual POSIX lifetime boundary, including SIGKILL."""

    def check_launcher_termination(self, whole_session):
        """Echo SMT bytes unchanged and retain the actual solver wait after launcher death."""
        with tempfile.TemporaryDirectory() as directory:
            command = [
                sys.executable,
                str(PROBE), directory, sys.executable, '-u', '-c',
                'import sys; line=sys.stdin.buffer.readline(); '
                'sys.stdout.buffer.write(line); sys.stdout.buffer.flush(); '
                'sys.stdin.buffer.read()'
            ]
            with subprocess.Popen(command,
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE,
                                  start_new_session=True) as child:
                payload = b'(check-sat)\n'
                child.stdin.write(payload)
                child.stdin.flush()
                self.assertEqual(child.stdout.read(len(payload)), payload)
                if whole_session:
                    os.killpg(child.pid, signal.SIGHUP)
                else:
                    child.kill()
                self.assertEqual(child.wait(timeout=5), -1 if whole_session else -9)
                child.stdin.close()
                deadline = time.monotonic() + 5
                while not list(Path(directory).glob('*.finished.json')):
                    self.assertLess(time.monotonic(), deadline, 'Missing actual solver wait')
                    time.sleep(0.05)
            start = json.loads(next(Path(directory).glob('*.started.json')).read_text())
            end = json.loads(next(Path(directory).glob('*.finished.json')).read_text())
            self.assertEqual(start['child_pid'], end['child_pid'])
            self.assertEqual(end['actual_exit'], 0)
            self.assertNotEqual(end['waiter_pid'], end['wrapper_pid'])

    def test_hard_killed_launcher_still_records_solver_eof_exit(self):
        """Match the runtime's immediate-child SIGKILL teardown."""
        self.check_launcher_termination(False)

    def test_pty_session_hangup_still_records_solver_eof_exit(self):
        """Match the regression harness's controlling-terminal SIGHUP teardown."""
        self.check_launcher_termination(True)

    def test_nonzero_solver_exit_is_preserved(self):
        """A failed solver must remain failed through both actual wait operations."""
        with tempfile.TemporaryDirectory() as directory:
            result = subprocess.run([
                sys.executable,
                str(PROBE), directory, sys.executable, '-c', 'raise SystemExit(7)'
            ],
                                    check=False)
            self.assertEqual(result.returncode, 7)
            receipt = json.loads(next(Path(directory).glob('*.finished.json')).read_text())
            self.assertEqual(receipt['actual_exit'], 7)


if __name__ == '__main__':
    unittest.main()
