#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# Test method names describe the assertions; fixture helpers stay concise.
# pylint: disable=missing-function-docstring
"""Exercise actual subprocess failures, provenance, logs, and the Bash gate."""

import copy
import importlib.util
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import check_results
import run_regressions

SOURCE_ROOT = Path(__file__).resolve().parents[2]
GROUPS = run_regressions.GROUPS


def summary(count, status="PASSED", extras=""):
    """Build a completed harness summary for subprocess and log fixtures."""
    return f"==TESTS DONE, {status}: Passed {count}  Failed 0{extras}  Time 0:01\n"


class ResultsTest(unittest.TestCase):
    """Check strict results validation using an isolated Git checkout."""

    def setUp(self):
        # unittest cleanups run even when setUp fails before a test starts.
        self.temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for directory in ("logs", "out", "test_regress/t"):
            (self.root / directory).mkdir(parents=True)
        for arguments in (("init", "--quiet"),
                          ("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                           "commit", "--quiet", "--allow-empty", "-m", "Fixture")):
            subprocess.run(["git", *arguments], cwd=self.root, check=True, capture_output=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=self.root,
                                            text=True).strip()
        (self.root / "out/provenance.txt").write_text(self.head + "\n")
        self.results = {}
        self.config = {}
        for group, names in GROUPS.items():
            count = len(names)
            self.results[group] = {
                "commit": self.head,
                "selected": names,
                "expected": count,
                "returncode": 0,
                "counts": {
                    "passed": count,
                    "failed": 0
                },
                "summary_status": "PASSED",
                "success": True
            }
            self.log(group).write_text(summary(count))
            self.config["t/t_" + names[0] + ".py"] = {"output": summary(count), "returncode": 0}
            for name in names:
                (self.root / "test_regress/t" / ("t_" + name + ".py")).touch()
        # These processes really exit with the selected status, just as the
        # regression harness does. No mocked Popen/wait masks an exit failure.
        (self.root / "test_regress/driver.py").write_text(
            "import json, sys\n"
            "from pathlib import Path\n"
            "config = json.loads(Path('fixture-config.json').read_text())\n"
            "driver = next(arg for arg in sys.argv[1:] if arg.startswith('t/'))\n"
            "result = config[driver]\n"
            "print(result['output'], end='')\n"
            "sys.exit(result['returncode'])\n")

    def log(self, group):
        return self.root / "logs" / (group + "-regressions.log")

    def verify(self):
        (self.root / "out/regression-results.json").write_text(json.dumps(self.results))
        with redirect_stdout(io.StringIO()):
            check_results.check_results(self.root)

    def rejected(self):
        with self.assertRaises(SystemExit):
            self.verify()

    def run_fixture(self):
        (self.root / "test_regress/fixture-config.json").write_text(json.dumps(self.config))
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            status = run_regressions.run_groups(self.root, list(GROUPS))
        self.results = json.loads((self.root / "out/regression-results.json").read_text())
        return status

    def test_complete_selection(self):
        self.assertEqual(self.run_fixture(), 0)
        self.assertEqual(sum(result["counts"]["passed"] for result in self.results.values()),
                         sum(map(len, GROUPS.values())))
        self.verify()
        # An ordinary cloud checkout has neither build-created output directory.
        shutil.rmtree(self.root / "logs")
        shutil.rmtree(self.root / "out")
        self.assertEqual(self.run_fixture(), 0)
        self.assertTrue((self.root / "logs").is_dir())
        self.assertTrue((self.root / "out").is_dir())
        (self.root / "out/provenance.txt").write_text(self.head + "\n")
        self.verify()

    def test_missing_extra_and_empty_groups(self):
        original = copy.deepcopy(self.results)
        for results in ({}, {
                key: value
                for key, value in original.items() if key != "upstream"
        }, dict(original, unexpected=original["upstream"])):
            with self.subTest(groups=list(results)):
                self.results = results
                self.rejected()

    def test_recorded_failures_and_incomplete_counts(self):
        original = copy.deepcopy(self.results)
        mutations = [{
            "returncode": 7
        }, {
            "success": False
        }, {
            "success": 1
        }, {
            "expected": 999
        }, {
            "expected": True
        }, {
            "returncode": False
        }, {
            "summary_status": "FAILED"
        }, {
            "commit": "0" * 40
        }, {
            "selected": list(reversed(GROUPS["upstream"]))
        }, {
            "counts": {
                "passed": len(GROUPS["upstream"]) - 1,
                "failed": 0
            }
        }, {
            "counts": {
                "passed": len(GROUPS["upstream"]),
                "failed": 1
            }
        }, {
            "counts": {
                "passed": len(GROUPS["upstream"]),
                "failed": False
            }
        }, {
            "counts": None
        }]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.results = copy.deepcopy(original)
                self.results["upstream"].update(mutation)
                self.rejected()
        self.results = copy.deepcopy(original)
        self.results["upstream"] = None
        self.rejected()

    def test_provenance_mismatch_and_empty(self):
        for provenance in ("0" * 40 + "\n", ""):
            with self.subTest(provenance=provenance):
                (self.root / "out/provenance.txt").write_text(provenance)
                self.rejected()

    def test_actual_logs_override_recorded_success(self):
        count = len(GROUPS["upstream"])
        for output in (summary(count - 1), summary(count,
                                                   "FAILED"), summary(count) + summary(count),
                       "No final summary\n", summary(count, extras="  Skipped 1")):
            with self.subTest(output=output):
                self.log("upstream").write_text(output)
                self.rejected()
        self.log("upstream").unlink()
        self.rejected()

    def test_subprocess_nonzero_despite_green_summary(self):
        self.config["t/t_" + GROUPS["fourstate"][0] + ".py"]["returncode"] = 7
        self.assertEqual(self.run_fixture(), 1)
        self.assertEqual(self.results["fourstate"]["returncode"], 7)
        self.assertFalse(self.results["fourstate"]["success"])
        # Later groups must still be executed and recorded for diagnosis.
        self.assertTrue(self.results["upstream"]["success"])
        self.rejected()

    def test_zero_exit_does_not_hide_failed_or_partial_summary(self):
        first = "t/t_" + GROUPS["fourstate"][0] + ".py"
        count = len(GROUPS["fourstate"])
        for output in (summary(count, "FAILED"), summary(count - 1),
                       summary(count,
                               extras="  Failed-First 1"), summary(count, extras="  Skipped 1"),
                       summary(count, extras="  Left 1"), summary(count, extras="  Running 1"),
                       summary(count) + summary(count), "No final summary\n"):
            with self.subTest(output=output):
                self.config[first]["output"] = output
                self.assertEqual(self.run_fixture(), 1)
                self.assertFalse(self.results["fourstate"]["success"])
                self.rejected()

    def test_invalid_group_selection(self):
        for groups in ([], ["unknown"], ["fourstate", "fourstate"]):
            with self.subTest(groups=groups), self.assertRaises(ValueError):
                run_regressions.run_groups(self.root, groups)


class BashGateTest(unittest.TestCase):
    """Exercise the build's actual shell gate with each failing subprocess."""

    def test_build_gate_propagates_smoke_regression_and_checker_failures(self):
        source = (SOURCE_ROOT / "ci/portable/build.bash").read_text()
        smoke = source[source.index("    smoke_status=0\n"):source.index("\nfi\n# The harness")]
        gate = source[source.index("regress_status=0\n"):source.
                      index("\npython3 - <<'PY'\nimport hashlib,pathlib")]
        shell = os.environ.get("BASH_BIN") or shutil.which("bash")
        version = subprocess.check_output([shell, "--version"], text=True).splitlines()[0]
        print("Validation gate shell: " + version)
        fixture = """set -euo pipefail
python3() {
    case "$1" in
        ci/portable/smoke.py) return "$SMOKE_FIXTURE_STATUS" ;;
        ci/portable/run_regressions.py) return "$REGRESS_FIXTURE_STATUS" ;;
        ci/portable/check_results.py) return "$CHECKER_FIXTURE_STATUS" ;;
        *) return 99 ;;
    esac
}
""" + smoke + "\n" + gate + "\necho VALIDATION_PASSED\n"
        for statuses in ((0, 0, 0), (9, 0, 0), (0, 7, 0), (0, 0, 5), (9, 7, 0)):
            with self.subTest(statuses=statuses):
                environment = dict(os.environ)
                for key, status in zip(("SMOKE", "REGRESS", "CHECKER"), statuses):
                    environment[key + "_FIXTURE_STATUS"] = str(status)
                result = subprocess.run([shell, "-c", fixture],
                                        check=False,
                                        env=environment,
                                        text=True,
                                        capture_output=True)
                self.assertEqual(result.returncode == 0, statuses == (0, 0, 0), result.stderr)
                self.assertEqual("VALIDATION_PASSED" in result.stdout, statuses == (0, 0, 0))


class EnumHashTest(unittest.TestCase):
    """Ensure enum hash normalization preserves identity and structure."""

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("regression_driver",
                                                      SOURCE_ROOT / "test_regress/driver.py")
        cls.driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.driver)

    def compare(self, actual, expected, normalize=True):
        test = object.__new__(self.driver.VlTest)
        errors = []
        test.error_keep_going = errors.append
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            # Isolate the comparison engine without compiler or filesystem setup.
            # pylint: disable=protected-access
            test._files_identical_reader(io.StringIO(actual),
                                         io.StringIO(expected),
                                         fn1="actual",
                                         fn2="expected",
                                         is_logfile=False,
                                         strip_hex=False,
                                         normalize_enum_hash=normalize,
                                         moretry=False)
            # pylint: enable=protected-access
        return not errors

    def test_only_generated_enum_hash_is_normalized(self):
        actual = "__Venum_h123abcde__0 = __Venum_h123abcde__0;\n"
        golden = "__Venum_hHASH0__0 = __Venum_hHASH0__0;\n"
        self.assertTrue(self.compare(actual, golden))
        self.assertTrue(self.compare(actual.replace("123abcde", "87654321"), golden))
        self.assertFalse(self.compare(actual, golden, normalize=False))
        self.assertFalse(self.compare(actual + "32'h123abcde\n", golden + "32'h87654321\n"))
        self.assertFalse(self.compare(actual.replace("__0;", "__1;"), golden))
        self.assertFalse(self.compare(actual.replace("__Venum_", "__Vother_"), golden))

    def test_distinct_hashes_and_alias_relationships_remain_distinct(self):
        actual = "__Venum_h123abcde__0 __Venum_h123abcde__1 __Venum_h87654321__0\n"
        golden = "__Venum_hHASH0__0 __Venum_hHASH0__1 __Venum_hHASH1__0\n"
        self.assertTrue(self.compare(actual, golden))
        self.assertFalse(self.compare(actual.replace("87654321", "123abcde"), golden))
        self.assertFalse(self.compare(actual.replace("123abcde__1", "87654321__1"), golden))


if __name__ == "__main__":
    unittest.main()
