#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# Method names describe these subprocess controls, not HDL simulation coverage.
# pylint: disable=missing-function-docstring
"""Exercise actual native exits, stream contracts and fail-closed batch accounting."""

import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest

import icarus_sweep as sweep


def normal_row():
    """Build a contract fixture; no fixture is claimed as an HDL test."""
    return {
        "family": "perl-vvp",
        "effective_type": "normal",
        "gold_mode": "selfchecking_passed_line",
        "source": {
            "exists": True
        },
        "parser_fields": {
            "testmod": "top",
            "plargs": "+value=17"
        },
        "iverilog_args": ["-g2001-noconfig", "-DVALUE=17"]
    }


class SweepControls(unittest.TestCase):
    """Use real children, their actual wait4 receipts, and physical file bytes."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)

    def stage(self, name, program, timeout=5):
        return sweep.stage(self.root, name, [sys.executable, "-c", program], self.root, timeout,
                           dict(os.environ), 0)

    def test_child_pid_and_both_streams_match_native_receipt(self):
        record = self.stage(
            "run", 'import os,sys; print(os.getpid()); '
            'print("separate stderr",file=sys.stderr)')
        self.assertEqual(record["actual_exit"], 0)
        self.assertEqual(int(Path(record["stdout"]).read_text()), record["pid"])
        self.assertEqual(Path(record["stderr"]).read_text(), "separate stderr\n")
        self.assertEqual(record["stdout_sha256"], sweep.sha256(record["stdout"]))
        self.assertEqual(record["stderr_sha256"], sweep.sha256(record["stderr"]))
        native = json.loads((self.root / "run.finished.json").read_text())
        self.assertEqual(native["pid"], record["pid"])
        self.assertEqual(native["raw_wait_status"], 0)

    def test_nonzero_is_not_masked_by_success_text(self):
        record = self.stage("compile", 'import sys; print("PASSED"); sys.exit(7)')
        self.assertEqual(record["actual_exit"], 7)
        self.assertEqual(record["raw_wait_status"], 7 << 8)
        self.assertEqual(record["observer_exit"], 7)
        self.assertEqual(sweep.stage_status(record, "COMPILE_FAILED"), "COMPILE_FAILED")

    def test_runtime_failed_line_is_not_masked_by_passed_lines(self):
        record = self.stage("run", 'print("FAILED\\nPASSED\\nPASSED")')
        self.assertEqual(record["actual_exit"], 0)
        self.assertEqual(record["failure_guard_lines"], ["FAILED"])
        self.assertEqual(sweep.stage_status(record, "RUNTIME_FAILED"), "FAILURE_GUARD")

    def test_compile_warning_source_excerpt_is_not_model_execution(self):
        diagnostic = ('%Warning-REALCVT: source.v:16:6: warning\n'
                      ' 16 | $display("FAILED -- bad result");')
        record = self.stage("compile", f"print({diagnostic!r})")
        self.assertEqual(record["actual_exit"], 0)
        self.assertEqual(record["failure_guard_lines"], [])
        self.assertIsNone(sweep.stage_status(record, "COMPILE_FAILED"))

    def test_zero_exit_cannot_hide_primary_compile_error(self):
        record = self.stage("compile", 'print("%Error: actual tool error\\nPASSED")')
        self.assertEqual(record["actual_exit"], 0)
        self.assertEqual(sweep.stage_status(record, "COMPILE_FAILED"), "FAILURE_GUARD")

    def test_pure_unsupported_remains_an_explicit_diagnostic(self):
        record = self.stage(
            "compile", 'import sys; '
            'print("%Error-UNSUPPORTED: legal feature not implemented\\n'
            '%Error: Exiting due to 1 error(s)"); sys.exit(1)')
        self.assertTrue(sweep.unsupported_only(record))

    def test_mixed_errors_are_not_classified_as_pure_unsupported(self):
        record = self.stage(
            "compile", 'import sys; '
            'print("%Error-UNSUPPORTED: unsupported feature\\n'
            '%Error: ordinary parse error\\n'
            '%Error: Exiting due to 2 error(s)"); sys.exit(1)')
        self.assertFalse(sweep.unsupported_only(record))

    def test_internal_fault_is_not_classified_as_unsupported(self):
        record = self.stage(
            "compile", 'import sys; '
            'print("%Error-UNSUPPORTED: unsupported feature\\n'
            '%Error: Verilator internal fault"); sys.exit(1)')
        self.assertFalse(sweep.unsupported_only(record))

    def test_timeout_is_not_a_pass(self):
        record = self.stage("run", 'import time; time.sleep(2)', timeout=0.1)
        self.assertNotEqual(record["actual_exit"], 0)
        self.assertEqual(record["termination_reason"], "timeout")
        self.assertEqual(sweep.stage_status(record, "RUNTIME_FAILED"), "TIMEOUT")

    def test_missing_tool_is_infrastructure_failure(self):
        record = sweep.stage(self.root, "compile", [self.root / "missing-tool"], self.root, 5,
                             dict(os.environ), 0)
        self.assertEqual(record["actual_exit"], 127)
        self.assertEqual(sweep.stage_status(record, "COMPILE_FAILED"), "INFRASTRUCTURE_ERROR")

    def test_existing_stage_cannot_overwrite_evidence(self):
        first = self.stage("run", 'print("first output")')
        digest = sweep.sha256(first["stdout"])
        with self.assertRaises(ValueError):
            self.stage("run", 'print("replacement")')
        self.assertEqual(sweep.sha256(first["stdout"]), digest)

    def test_fixture_copy_preserves_executable_helpers(self):
        repo = self.root / "repo"
        (repo / "ivtest").mkdir(parents=True)
        helper = repo / "ivtest/helper.sh"
        helper.write_text("#!/bin/sh\nexit 0\n")
        helper.chmod(0o755)
        target = self.root / "fixture"
        sweep.copy_fixture(repo, {"ivtest/helper.sh": {}}, target)
        self.assertEqual(stat.S_IMODE((target / "helper.sh").stat().st_mode), 0o755)
        self.assertEqual((target / "helper.sh").read_bytes(), helper.read_bytes())

    def test_noconfig_mode_and_original_arguments_are_preserved(self):
        row = normal_row()
        result = sweep.adapter(row)
        self.assertEqual(result["status"], "READY")
        self.assertIn("1364-2001-noconfig", result["verilator_args"])
        self.assertEqual(result["original_iverilog_args"],
                         ["-D__ICARUS_UNSIZED__", "-g2001-noconfig", "-DVALUE=17"])
        self.assertEqual(result["runtime_args"], ["+value=17"])
        self.assertEqual(result["verilator_args"][-2:], ["--top-module", "top"])

    def test_unknown_flags_and_vpi_are_adapter_gaps(self):
        row = normal_row()
        row["iverilog_args"].append("-gicarus-misc")
        result = sweep.adapter(row)
        self.assertEqual(result["status"], "ADAPTER_UNIMPLEMENTED")
        self.assertEqual(result["translation_ledger"][-1]["verilator"], None)
        row = {
            "family": "vpi",
            "effective_type": "normal",
            "gold_mode": "compiler_and_runtime_log",
            "source": {
                "exists": True
            }
        }
        self.assertEqual(sweep.adapter(row)["status"], "ADAPTER_UNIMPLEMENTED")

    def test_python_runtime_oracle_does_not_accept_stderr_passed(self):
        # This is a small stream-contract control, not an Icarus implementation.
        (self.root / "run_ivl.py").write_text(
            'def check_run_outputs(options,text,logs,expected):\n'
            '    return [0 if text == "PASSED\\n" else 1,"stream control"]\n')
        executed = self.stage(
            "run", 'import sys; print("not passed"); '
            'print("PASSED",file=sys.stderr)')
        row = {"family": "python-vvp", "parser_fields": {"gold": None, "diff": None}}
        args = SimpleNamespace(timeout=5, min_disk_bytes=0)
        oracle = sweep.run_oracle(self.root, self.root, row, executed, args, dict(os.environ))
        self.assertEqual(oracle["actual_exit"], 1)
        self.assertEqual(sweep.stage_status(oracle, "ORACLE_FAILED"), "ORACLE_FAILED")

    def test_complete_denominator_and_unrun_slots_remain_visible(self):
        summary = sweep.summarize([], 128)
        self.assertEqual(summary["full_default_denominator"], 3850)
        self.assertEqual(summary["unselected_UNRUN"], 3722)
        self.assertEqual(summary["selected_unrun"], 128)
        self.assertFalse(summary["full_suite_complete"])
        reference = {"status": "PASS", "runtime_executed": True}
        unresolved = {"status": "FAILURE_GUARD", "runtime_executed": True}
        self.assertEqual(sweep.pair_status(reference, unresolved), "UNREVIEWED_OUTPUT_DIFFERENCE")


if __name__ == "__main__":
    unittest.main()
