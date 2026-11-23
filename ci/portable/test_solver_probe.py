#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Check real child waits and protocol bytes when the runtime kills its launcher."""
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

PROBE = Path(__file__).with_name('solver_probe.py')


class SolverProbeTest(unittest.TestCase):
    """Exercise the actual POSIX lifetime boundary, including SIGKILL."""

    def test_hard_killed_launcher_still_records_solver_eof_exit(self):
        """Echo SMT bytes unchanged, kill the launcher, and observe the real child's zero exit."""
        with tempfile.TemporaryDirectory() as directory:
            command = [
                sys.executable,
                str(PROBE), directory, sys.executable, '-u', '-c',
                'import sys; line=sys.stdin.buffer.readline(); '
                'sys.stdout.buffer.write(line); sys.stdout.buffer.flush(); '
                'sys.stdin.buffer.read()'
            ]
            with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as child:
                payload = b'(check-sat)\n'
                child.stdin.write(payload)
                child.stdin.flush()
                self.assertEqual(child.stdout.read(len(payload)), payload)
                child.kill()
                self.assertEqual(child.wait(timeout=5), -9)
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
