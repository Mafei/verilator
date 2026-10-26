#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require complete, bounded, regular wave files for finish and SV controls."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import log_evidence


class FinishWaveEvidenceTest(unittest.TestCase):
    """Reject incomplete or indirect collections and preserve all wave bytes."""

    def setUp(self):
        # unittest cleanups own the directory across each test's lifecycle.
        self.temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
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


class ControlsWaveEvidenceTest(unittest.TestCase):
    """Check all seventeen control profiles using independent complete wave fixtures."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        fixtures = ("t_fourstate_port_init", "t_fourstate_port_partial", "t_fourstate_port_static",
                    "t_fourstate_nba_capture", "t_fourstate_nba_race", "t_fourstate_nba_tasks",
                    "t_fourstate_nba_trigger", "t_fourstate_nba_unknown",
                    "t_fourstate_array_guard")
        self.paths = [
            self.root / "test_regress/obj_vlt" / fixture / "simx.vcd" for fixture in fixtures
        ]
        self.paths += [
            self.root / "test_regress/obj_vlt/t_fourstate_array_init" / ("width" + str(width)) /
            "simx.vcd" for width in (7, 33, 65)
        ]
        self.api_paths = [
            self.root / "test_regress/obj_vlt/t_fourstate_port_api" / profile / "simx.vcd"
            for profile in ("default", "on", "off")
        ]
        self.trace_paths = [
            self.root / "test_regress/obj_vlt/t_fourstate_trace_resume" / profile / "simx.vcd"
            for profile in ("two_state", "four_state")
        ]
        self.paths += self.api_paths + self.trace_paths
        self.raw = (b"$timescale 1ps $end\n$scope module t $end\n"
                    b"$var wire 1 ! q $end\n$upscope $end\n"
                    b" $enddefinitions $end\n#0\n0!\n#1\n1!\n")
        for path in self.paths:
            path.parent.mkdir(parents=True)
            path.write_bytes(self.raw)

    def emit(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            log_evidence.controls_wave_evidence(self.root)
        return output.getvalue()

    def test_all_seventeen_controls_preserve_complete_bytes(self):
        console = self.emit()
        result = json.loads((self.root / "out/controls-wave-evidence.json").read_text())
        self.assertEqual(len(result["records"]), 17)
        self.assertEqual(result["budget_bytes"], 512 * 1024)
        self.assertEqual(result["total_bytes"], sum(path.stat().st_size for path in self.paths))
        self.assertEqual(json.loads(console.removeprefix("CONTROLS_WAVE_BYTES ")), result)
        for record, path in zip(result["records"], self.paths):
            self.assertEqual(record["path"], str(path.relative_to(self.root)))
            self.assertEqual(record["contents_utf8"].encode(), path.read_bytes())
            self.assertEqual(record["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_flat_control_rejects_partial_collection(self):
        self.paths[0].unlink()
        with self.assertRaisesRegex(ValueError, "Missing or unexpected control VCD"):
            self.emit()

    def test_missing_array_width_rejects_partial_collection(self):
        path = self.root / "test_regress/obj_vlt/t_fourstate_array_init/width65/simx.vcd"
        path.unlink()
        with self.assertRaisesRegex(ValueError, "Missing or unexpected control VCD"):
            self.emit()

    def test_missing_api_profile_rejects_partial_collection(self):
        for path in self.api_paths:
            with self.subTest(profile=path.parent.name):
                path.unlink()
                with self.assertRaisesRegex(ValueError, "Missing or unexpected control VCD"):
                    self.emit()
                path.write_bytes(self.raw)

    def test_missing_trace_profile_rejects_partial_collection(self):
        for path in self.trace_paths:
            with self.subTest(profile=path.parent.name):
                path.unlink()
                with self.assertRaisesRegex(ValueError, "Missing or unexpected control VCD"):
                    self.emit()
                path.write_bytes(self.raw)

    def test_extra_flat_or_nested_wave_rejects_stale_collection(self):
        for extra in (self.paths[0].with_name("stale.vcd"),
                      self.paths[-1].parent.parent / "width95/simx.vcd"):
            with self.subTest(extra=extra):
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_bytes(self.raw)
                with self.assertRaisesRegex(ValueError, "Missing or unexpected control VCD"):
                    self.emit()
                extra.unlink()

    def test_symlinked_wave_rejects_indirect_bytes(self):
        path = self.paths[0]
        target = path.with_name("indirect.txt")
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "Symlinked control output"):
            self.emit()

    def test_symlinked_profile_rejects_redirected_collection(self):
        directory = self.paths[-1].parent
        moved = directory.with_name("redirected")
        directory.rename(moved)
        directory.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlinked control output"):
            self.emit()

    def test_collection_budget_rejects_oversize_output(self):
        self.paths[-1].write_bytes(self.raw + b"\n" * (512 * 1024))
        with self.assertRaisesRegex(ValueError, "Empty or oversized semantic VCD collection"):
            self.emit()

    def test_incomplete_wave_rejects_header_or_time_truncation(self):
        for bad in (b"#0\n0!\n", self.raw.split(b"#0")[0], self.raw.rstrip(b"\n")):
            with self.subTest(raw=bad):
                self.paths[-1].write_bytes(bad)
                with self.assertRaisesRegex(ValueError, "Incomplete control VCD"):
                    self.emit()


class SVSemanticsWaveEvidenceTest(unittest.TestCase):
    """Require every new public semantic profile without trimming any wave bytes."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        fixtures = ("t_fourstate_inout_default", "t_fourstate_nba_partselect_clip",
                    "t_fourstate_nba_repeat_control", "t_fourstate_sen_expr",
                    "t_fourstate_sen_iff", "t_timing_nba_partselect_clip",
                    "t_timing_nba_repeat_control", "t_tri_inout_default",
                    "t_fourstate_slice_index_domain", "t_fourstate_slice_packed_domain")
        self.paths = [
            self.root / "test_regress/obj_vlt" / fixture / "simx.vcd" for fixture in fixtures
        ]
        self.raw = (b"$timescale 1ps $end\n$scope module t $end\n"
                    b"$var wire 1 ! q $end\n$upscope $end\n"
                    b"$enddefinitions $end\n#0\n0!\n#1\n1!\n")
        for path in self.paths:
            path.parent.mkdir(parents=True)
            path.write_bytes(self.raw)

    def emit(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            log_evidence.sv_semantics_wave_evidence(self.root)
        return output.getvalue()

    def test_all_ten_profiles_preserve_complete_bytes(self):
        console = self.emit()
        result = json.loads((self.root / "out/sv-semantics-wave-evidence.json").read_text())
        self.assertEqual(len(result["records"]), 10)
        self.assertEqual(result["total_bytes"], sum(path.stat().st_size for path in self.paths))
        self.assertEqual(json.loads(console.removeprefix("SV_SEMANTICS_WAVE_BYTES ")), result)
        for record, path in zip(result["records"], self.paths):
            self.assertEqual(record["path"], str(path.relative_to(self.root)))
            self.assertEqual(record["contents_utf8"].encode(), path.read_bytes())
            self.assertEqual(record["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_missing_profile_rejects_partial_collection(self):
        self.paths[-1].unlink()
        with self.assertRaisesRegex(ValueError, "Missing or unexpected SV semantic VCD"):
            self.emit()

    def test_extra_nested_wave_rejects_ambiguous_collection(self):
        path = self.paths[0].parent / "stale/extra.vcd"
        path.parent.mkdir()
        path.write_bytes(self.raw)
        with self.assertRaisesRegex(ValueError, "Missing or unexpected SV semantic VCD"):
            self.emit()

    def test_symlinked_parent_rejects_redirected_collection(self):
        base = self.root / "test_regress/obj_vlt"
        moved = base.with_name("redirected")
        base.rename(moved)
        base.symlink_to(moved, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "Symlinked SV semantic fixture"):
            self.emit()

    def test_symlinked_wave_rejects_indirect_bytes(self):
        path = self.paths[0]
        target = path.with_name("indirect.txt")
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "Nonregular semantic VCD"):
            self.emit()

    def test_budget_rejects_oversize_collection(self):
        self.paths[-1].write_bytes(self.raw + b"\n" * log_evidence.SV_SEMANTICS_WAVE_BUDGET)
        with self.assertRaisesRegex(ValueError, "Empty or oversized semantic VCD collection"):
            self.emit()

    def test_incomplete_wave_rejects_header_time_or_newline_truncation(self):
        for raw in (b"#0\n0!\n", self.raw.split(b"#0")[0], self.raw.rstrip(b"\n")):
            with self.subTest(raw=raw):
                self.paths[-1].write_bytes(raw)
                with self.assertRaisesRegex(ValueError, "Incomplete control VCD"):
                    self.emit()


if __name__ == "__main__":
    unittest.main()
