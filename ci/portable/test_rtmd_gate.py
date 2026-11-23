#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Exercise the actual focused collector and final shell gate together."""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class RtmdGateTest(unittest.TestCase):
    """A failed focus collector must hold without suppressing original acceptance."""

    def test_focus_failure_keeps_original_collectors_and_fails_the_gate(self):
        """Execute the real shell snippets with controlled subprocess outcomes."""
        source = (ROOT / 'ci/portable/build.bash').read_text(encoding='utf-8')
        focus = source[source.index('rtmd_focus_status=0\n'):source.index(
            'if [[ $platform == macos-arm64 ]]; then\n    mkdir -p /tmp/verilator-relocated')]
        tail = source[source.index('# The harness uses this checkout'):]
        shell = shutil.which('bash')
        self.assertIsNotNone(shell)
        fixture = '''set -euo pipefail
root=$PWD
git() { printf '%040d\\n' 1; }
python3() {
    printf '%s\\n' "$*" >> calls.log
    if [[ $1 == ci/portable/focus_rtmd.py ]]; then return "$FOCUS_STATUS"; fi
    return 0
}
''' + focus + tail
        for status in (0, 7, 143):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                result = subprocess.run([shell, '-c', fixture],
                                        cwd=directory,
                                        env={
                                            **os.environ, 'FOCUS_STATUS': str(status)
                                        },
                                        capture_output=True,
                                        text=True,
                                        check=False)
                calls = (Path(directory) / 'calls.log').read_text(encoding='utf-8')
                self.assertEqual(result.returncode, 0 if status == 0 else 1, result.stderr)
                self.assertIn(f'RTMD_FOCUS_EXIT={status}', result.stdout)
                self.assertEqual(calls.count('ci/portable/focus_rtmd.py\n'), 1)
                self.assertIn('ci/portable/run_regressions.py fourstate integration', calls)
                self.assertIn('upstream_daily_20261114 upstream_rtmd_20261123', calls)
                self.assertIn('ci/portable/icarus_acceptance.py check --full18', calls)
                self.assertIn('ci/portable/finish_acceptance.py check', calls)
                self.assertIn('ci/portable/log_evidence.py results', calls)


if __name__ == '__main__':
    unittest.main()
