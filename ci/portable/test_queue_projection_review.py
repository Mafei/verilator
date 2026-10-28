#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Synthetic case122 corruption controls; no compiler or model executions."""
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import queue_projection_review as review


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class ProjectionReviewTest(unittest.TestCase):
    """Reject changed identities, missing runs and fabricated green contracts."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.pair = self.root / "pair"
        self.source = self.root / "source"
        self.recorded = Path("/work/pair")
        self.head = "a" * 40
        compiler = self.root / "bin/verilator_bin"
        compiler.parent.mkdir()
        compiler.write_bytes(b"synthetic compiler")
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(
            mock.patch.object(review.subprocess, "check_output", return_value=self.head))
        self.stack.enter_context(mock.patch.object(review, "GROUPS",
                                                   {review.GROUP: [review.NAME]}))
        for relative, constant, content in [(review.SOURCE, "SOURCE_SHA", b"x" * 780),
                                            (review.CONFIG, "CONFIG_SHA", b"{}"),
                                            (review.ORACLE, "ORACLE_SHA", b"# synthetic oracle")]:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            self.stack.enter_context(mock.patch.object(review, constant, review.sha(path)))
        self.contract = {
            "scenario_id": review.SID,
            "family": "python-vvp",
            "effective_type": "normal",
            "effective_oracle": "selfchecking_passed_line",
            "oracle": review.ORACLE,
            "iverilog_args": review.FLAGS,
            "parser_fields": review.PARSER_FIELDS,
            "source": {
                "path": review.SOURCE,
                "bytes": 780,
                "sha256": review.SOURCE_SHA
            }
        }
        self.inventory = self.root / "inventory.json"
        inventory = [{"scenario_id": "synthetic:" + str(i)} for i in range(3850)]
        inventory[122] = self.contract
        write(self.inventory, inventory)
        self.selection = self.root / "select.json"
        selected = [x["scenario_id"] for x in inventory[:128]]
        write(self.selection, {"scenario_ids": selected})
        self.stack.enter_context(
            mock.patch.object(review, "INVENTORY_SHA", review.sha(self.inventory)))
        self.stack.enter_context(
            mock.patch.object(review, "SELECTION_SHA", review.sha(self.selection)))
        self.binding = {
            "verilator_commit": self.head,
            "icarus_commit": review.fixed.PIN,
            "inventory_sha256": review.INVENTORY_SHA,
            "selection_sha256": review.SELECTION_SHA,
            "tools": {
                "verilator_bin": {
                    "sha256": review.sha(compiler)
                },
                "verilator_driver": {
                    "path": "/tools/verilator"
                },
                "iverilog": {
                    "path": "/tools/iverilog"
                }
            },
            "version": {
                "stdout": str(self.recorded / "version.stdout")
            }
        }
        self.row = {"scenario_id": review.SID, "pair_status": "UNREVIEWED_OUTPUT_DIFFERENCE"}
        for engine in ["icarus", "verilator"]:
            stages = {}
            for name in (["compile", "run", "oracle"]
                         if engine == "icarus" else ["compile", "build", "run", "oracle"]):
                stages[name] = self.native(engine, name)
            self.row[engine] = {
                "status": "PASS" if engine == "icarus" else "FAILURE_GUARD",
                "runtime_executed": True,
                "private_fixture_input_mutations": [],
                "original_oracle_accepted": engine == "icarus",
                "stages": stages
            }
        self.rows = [{"scenario_id": sid, "pair_status": "PASS_BOTH"} for sid in selected]
        self.publish()
        self.git_content = {}
        for suffix in ["py", "v"]:
            rel = "test_regress/t/t_" + review.NAME + "." + suffix
            self.git_content[rel] = b"synthetic committed input"
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.git_content[rel])
        self.stack.enter_context(
            mock.patch.object(review,
                              "git_bytes",
                              side_effect=lambda _r, _h, rel: self.git_content[rel]))
        write(
            self.root / "out/regression-results.json", {
                review.GROUP: {
                    "commit": self.head,
                    "selected": [review.NAME],
                    "expected": 1,
                    "returncode": 0,
                    "success": True,
                    "summary_status": "PASSED",
                    "counts": {
                        "passed": 1,
                        "failed": 0
                    }
                }
            })
        self.group = self.root / ("logs/" + review.GROUP + "-regressions.log")
        self.group.parent.mkdir()
        self.group.write_text("vlt/t_" + review.NAME + ": Self PASSED\n"
                              "==TESTS DONE, PASSED: Passed 1  Failed 0  Time 0:01\n")
        self.profile_root = self.root / ("test_regress/obj_vlt/t_" + review.NAME)
        for profile in ["two", "four"]:
            p = self.profile_root / profile / "run.log"
            p.parent.mkdir(parents=True)
            p.write_text("Queue projection checks: 100\n*-* All Finished *-*\n")

    def native(self, engine, name):
        actual = int(engine == "verilator" and name == "oracle")
        base = self.recorded / f"cases/0122/{engine}"
        if name == "compile":
            argv = ([
                "/tools/iverilog", "-o", "work/a.out", *review.FLAGS,
                review.PARSER_FIELDS["source"]
            ] if engine == "icarus" else [
                "/tools/verilator", "--cc", "--exe", "--main", "--assert", "--timing",
                "--fourstate", "--no-skip-identical", "-Wno-fatal", "--Mdir", "obj", "--prefix",
                "Vt", "--default-language", "1364-2005", "--default-language", "1800-2005",
                "-D__ICARUS_UNSIZED__", review.PARSER_FIELDS["source"]
            ])
        elif name == "oracle":
            argv = [
                "python3", "-c", review.ORACLE_PROGRAM,
                json.dumps(review.PARSER_FIELDS),
                str(base / "run.stdout")
            ]
        else:
            argv = [name]
        output = b""
        if name == "run":
            output = (b"PASSED\n" if engine == "icarus" else
                      b"FAILED line 26\nFAILED line 30\nFAILED line 33\nFAILED line 36\n")
        row = {
            "actual_exit": actual,
            "raw_wait_status": actual * 256,
            "pid": 123,
            "wait4_pid": 123,
            "termination_reason": None,
            "observer_exit": actual,
            "exited_normally": True,
            "kill_sent": False,
            "invoked_argv": argv
        }
        for label, suffix, content in [("log", ".log", b""), ("stdout", ".stdout", output),
                                       ("stderr", ".stderr", b""),
                                       ("output_log", ".output.log", output)]:
            row[label] = str(base / (name + suffix))
            path = self.pair / f"cases/0122/{engine}" / (name + suffix)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            row[label + "_bytes"] = len(content)
            row[label + "_sha256"] = review.sha(path)
        row["argv"] = [
            "bash", "-c", "synthetic launcher", "native-streams", row["stdout"], row["stderr"],
            *argv
        ]
        write(self.pair / f"cases/0122/{engine}/{name}.finished.json", row)
        return row

    def publish(self):
        self.rows[122] = copy.deepcopy(self.row)
        write(self.pair / "binding.json", self.binding)
        write(self.pair / "cases/0122/original-contract.json", self.contract)
        write(self.pair / "cases/0122/result.json", self.row)
        write(
            self.pair / "results.json", {
                "binding": self.binding,
                "results": self.rows,
                "summary": {
                    "pair_status_counts": {
                        "PASS_BOTH": 127,
                        "UNREVIEWED_OUTPUT_DIFFERENCE": 1
                    },
                    "protected_inputs_and_tools_unchanged": True,
                    "batch_gate_exit": 1
                }
            })

    def collect(self):
        return review.collect(self.root, self.pair, self.source, self.inventory, self.selection,
                              self.head)

    def test_conflict_keeps_original_failure_and_counts(self):
        result = self.collect()
        self.assertEqual(result["original_pair_status"], "UNREVIEWED_OUTPUT_DIFFERENCE")
        self.assertEqual(result["raw_pair_status_counts"]["UNREVIEWED_OUTPUT_DIFFERENCE"], 1)
        self.assertEqual(result["standard"]["status"], "PASS")
        self.assertFalse(result["overall_acceptance"])

    def test_changed_source_rejected(self):
        (self.source / review.SOURCE).write_text("changed")
        with self.assertRaises(ValueError):
            self.collect()

    def test_wrong_scenario_rejected(self):
        self.row["scenario_id"] = "another-case"
        self.publish()
        with self.assertRaises(ValueError):
            self.collect()

    def test_wrong_pin_rejected(self):
        self.binding["icarus_commit"] = "b" * 40
        self.publish()
        with self.assertRaises(ValueError):
            self.collect()

    def test_changed_inventory_hash_rejected(self):
        self.inventory.write_text("[]")
        with self.assertRaises(ValueError):
            self.collect()

    def test_original_failed_oracle_cannot_become_zero(self):
        record = self.row["verilator"]["stages"]["oracle"]
        record.update(actual_exit=0, raw_wait_status=0, observer_exit=0)
        write(self.pair / "cases/0122/verilator/oracle.finished.json", record)
        self.publish()
        with self.assertRaises(ValueError):
            self.collect()

    def test_runtime_not_executed_rejected(self):
        self.row["verilator"]["runtime_executed"] = False
        self.publish()
        with self.assertRaises(ValueError):
            self.collect()

    def test_private_input_mutations_are_rejected(self):
        for engine in ["icarus", "verilator"]:
            for value in (None, [{"path": "changed fixture"}]):
                with self.subTest(engine=engine, value=value):
                    self.row[engine].pop("private_fixture_input_mutations", None)
                    if value is not None:
                        self.row[engine]["private_fixture_input_mutations"] = value
                    self.publish()
                    with self.assertRaises((KeyError, ValueError)):
                        self.collect()
            self.row[engine]["private_fixture_input_mutations"] = []

    def test_unprotected_inputs_or_tools_are_rejected(self):
        path = self.pair / "results.json"
        original = json.loads(path.read_text())
        for value in (False, 1, None):
            with self.subTest(value=value):
                data = copy.deepcopy(original)
                data["summary"].pop("protected_inputs_and_tools_unchanged")
                if value is not None:
                    data["summary"]["protected_inputs_and_tools_unchanged"] = value
                write(path, data)
                with self.assertRaises((KeyError, ValueError)):
                    self.collect()

    def test_changed_compiler_binding_is_rejected(self):
        self.binding["tools"]["verilator_bin"]["sha256"] = "b" * 64
        self.publish()
        with self.assertRaises(ValueError):
            self.collect()

    def test_boolean_pair_gate_or_counts_are_rejected(self):
        path = self.pair / "results.json"
        original = json.loads(path.read_text())
        for change in [{
                "batch_gate_exit": True
        }, {
                "pair_status_counts": {
                    "PASS_BOTH": 127,
                    "UNREVIEWED_OUTPUT_DIFFERENCE": True
                }
        }]:
            with self.subTest(change=change):
                data = copy.deepcopy(original)
                data["summary"].update(change)
                write(path, data)
                with self.assertRaisesRegex(ValueError, "original_pair_summary_changed"):
                    self.collect()

    def test_changed_physical_compiler_is_rejected(self):
        (self.root / "bin/verilator_bin").write_bytes(b"different compiler")
        with self.assertRaises(ValueError):
            self.collect()

    def test_changed_compile_program_is_rejected(self):
        original = copy.deepcopy(self.row)
        for engine in ["icarus", "verilator"]:
            with self.subTest(engine=engine):
                self.row = copy.deepcopy(original)
                for recorded_engine in ["icarus", "verilator"]:
                    write(self.pair / f"cases/0122/{recorded_engine}/compile.finished.json",
                          self.row[recorded_engine]["stages"]["compile"])
                record = self.row[engine]["stages"]["compile"]
                record["invoked_argv"][0] = "/other/compiler"
                record["argv"][6:] = record["invoked_argv"]
                write(self.pair / f"cases/0122/{engine}/compile.finished.json", record)
                self.publish()
                with self.assertRaisesRegex(ValueError, "original_compile_program_changed"):
                    self.collect()

    def test_receipt_corruption_rejected(self):
        (self.pair / "cases/0122/verilator/run.stdout").write_text("PASSED\n")
        with self.assertRaises(ValueError):
            self.collect()

    def test_renamed_pass_not_accepted(self):
        self.row["pair_status"] = "PASS_BOTH"
        self.publish()
        with self.assertRaises(ValueError):
            self.collect()

    def test_missing_standard_profile_rejected(self):
        (self.profile_root / "four/run.log").unlink()
        with self.assertRaises(OSError):
            self.collect()

    def test_failed_standard_profile_rejected(self):
        with (self.profile_root / "four/run.log").open("a") as f:
            f.write("%Error: bad assertion\n")
        with self.assertRaises(ValueError):
            self.collect()

    def test_duplicate_harness_pass_rejected(self):
        with self.group.open("a") as f:
            f.write("vlt/t_" + review.NAME + ": Self PASSED\n")
        with self.assertRaises(ValueError):
            self.collect()

    def test_inconsistent_group_metadata_is_rejected(self):
        path = self.root / "out/regression-results.json"
        original = json.loads(path.read_text())
        for field, value in [("returncode", None), ("returncode", True), ("success", 1),
                             ("success", False), ("expected", True),
                             ("counts", {
                                 "passed": True,
                                 "failed": 0
                             })]:
            with self.subTest(field=field, value=value):
                data = copy.deepcopy(original)
                data[review.GROUP][field] = value
                write(path, data)
                with self.assertRaises(ValueError):
                    self.collect()
        data = copy.deepcopy(original)
        del data[review.GROUP]["returncode"]
        write(path, data)
        with self.assertRaises(KeyError):
            self.collect()

    def test_unrelated_group_failure_is_retained(self):
        names = [review.NAME, "synthetic_other"]
        self.group.write_text("vlt/t_" + review.NAME + ": Self PASSED\n"
                              "==TESTS DONE, FAILED: Passed 1  Failed 1  Time 0:01\n")
        write(
            self.root / "out/regression-results.json", {
                review.GROUP: {
                    "commit": self.head,
                    "selected": names,
                    "expected": 2,
                    "returncode": 10,
                    "success": False,
                    "summary_status": "FAILED",
                    "counts": {
                        "passed": 1,
                        "failed": 1
                    }
                }
            })
        with mock.patch.object(review, "GROUPS", {review.GROUP: names}):
            result = self.collect()
        self.assertEqual(result["standard"]["status"], "PASS")
        self.assertFalse(result["overall_acceptance"])

    def test_wrong_standard_count_rejected(self):
        (self.profile_root /
         "two/run.log").write_text("Queue projection checks: 99\n*-* All Finished *-*\n")
        with self.assertRaises(ValueError):
            self.collect()

    def test_uncommitted_standard_source_rejected(self):
        (self.root / ("test_regress/t/t_" + review.NAME + ".v")).write_text("changed")
        with self.assertRaises(ValueError):
            self.collect()

    def test_typed_relay_rejects_other_case_or_boolean_count(self):
        data = self.collect()
        self.assertFalse(review.core_fields(data)["overall_acceptance"])
        for bad in [
                dict(data, scenario_id="another-case"),
                dict(data, standard=dict(data["standard"], checks_per_profile=True))
        ]:
            with self.assertRaises(ValueError):
                review.core_fields(bad)

    def test_cli_failure_is_not_green(self):
        out = self.root / "failed-review.json"
        argv = [
            "review", "--expected-head", self.head, "--root",
            str(self.root), "--pair",
            str(self.pair), "--source",
            str(self.source), "--inventory",
            str(self.inventory), "--select",
            str(self.selection), "--output",
            str(out)
        ]
        with mock.patch.object(review, "collect", side_effect=ValueError("bad")), \
                mock.patch("sys.argv", argv), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(), 2)
        self.assertEqual(json.loads(out.read_text())["reviewed_classification"], "NOT_APPLIED")
        self.assertEqual(json.loads(out.read_text())["reason"], "ValueError: bad")


if __name__ == "__main__":
    unittest.main()
