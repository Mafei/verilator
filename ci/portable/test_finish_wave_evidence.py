#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require complete, bounded, regular wave files for all finish profiles."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import log_evidence


class FinishWaveEvidenceTest(unittest.TestCase):

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.files = []
        for fixture in ("t_timing_finish_boundary", "t_fourstate_finish_boundary"):
            for case in range(10):
                path = self.root / "test_regress/obj_vlt" / fixture / ("case" +
                                                                       str(case)) / "simx.vcd"
                path.parent.mkdir(parents=True)
                path.write_bytes(b"$enddefinitions $end\n#0\n0!\n")
                self.files.append(path)

    def emit(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            log_evidence.finish_wave_evidence(self.root)
        return output.getvalue()

    def test_all_twenty_profiles_preserve_complete_bytes(self):
        console = self.emit()
        result = json.loads((self.root / "out/finish-wave-evidence.json").read_text())
        self.assertEqual(len(result["records"]), 20)
        self.assertEqual(result["total_bytes"], sum(path.stat().st_size for path in self.files))
        self.assertEqual(json.loads(console.removeprefix("FINISH_WAVE_BYTES ")), result)
        for record, path in zip(result["records"], self.files):
            self.assertEqual(record["path"], str(path.relative_to(self.root)))
            self.assertEqual(record["contents_utf8"].encode(), path.read_bytes())
            self.assertEqual(record["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_profile_rejects_partial_collection(self):
        self.files[-1].unlink()
        with self.assertRaisesRegex(ValueError, "Missing or unexpected finish VCD"):
            self.emit()

    def test_extra_wave_rejects_ambiguous_profile(self):
        self.files[0].with_name("stale.vcd").write_bytes(b"stale")
        with self.assertRaisesRegex(ValueError, "Missing or unexpected finish VCD"):
            self.emit()

    def test_symlinked_case_rejects_redirected_collection(self):
        directory = self.files[0].parent
        moved = directory.with_name("redirected")
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlinked semantic fixture"):
            self.emit()

    def test_symlinked_wave_rejects_indirect_bytes(self):
        path = self.files[0]
        target = path.with_name("indirect.txt")
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "Nonregular semantic VCD"):
            self.emit()

    def test_collection_budget_rejects_oversize_output(self):
        self.files[-1].write_bytes(b"0" * (64 * 1024))
        with self.assertRaisesRegex(ValueError, "Empty or oversized semantic VCD collection"):
            self.emit()


if __name__ == "__main__":
    unittest.main()
