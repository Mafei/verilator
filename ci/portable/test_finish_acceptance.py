#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Exercise real child exits and immutable finish oracles; fake models certify only the gate."""
# pylint: disable=missing-function-docstring
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import finish_acceptance as acceptance

RECEIPTS = []


class FinishAcceptanceTest(unittest.TestCase):
    """Check original output failures, native receipts, complete collection, and tampering."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.repository = self.root / "source"
        (self.repository / "bin").mkdir(parents=True)
        compiler = self.repository / "bin/verilator_bin"
        compiler.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
obj = Path(sys.argv[sys.argv.index('--Mdir') + 1])
case = next((int(x.split('=')[1]) for x in sys.argv if x.startswith('+define+CASE=')), 9)
config = json.loads(Path(os.environ['FINISH_FIXTURE_CONFIG']).read_text())
if case == config.get('compile_fail_case'):
    print('Explicit native fixture compile failure')
    sys.exit(7)
obj.mkdir(parents=True)
(obj / 'Vt.mk').write_text('# Gate fixture: no C++ compilation.\\n')
q = 1 if case == 5 and config.get('wrong_finish5', True) else 0
first = 'OBS 9 callee_before 1' if case == 9 else 'OBS %d before %d' % (case, int(case != 0))
last = 'FINAL 7 A 1 q=0' if case == 7 else 'FINAL %d %d q=%d' % (case, int(case != 0), q)
text = first + '\\n'
if q:
    text += 'UNREACHABLE postponed_strobe\\n'
text += last + '\\n'
wave = '$timescale 1ps $end\\n$scope module t $end\\n$var wire 1 ! q $end\\n$upscope $end\\n$enddefinitions $end\\n#0\\n0!\\n'
if q:
    wave += '#1\\n1!\\n'
model = '#!/usr/bin/env python3\\nfrom pathlib import Path\\nimport sys\\nPath("wave.vcd").write_text(' + repr(wave) + ')\\nprint(' + repr(text) + ', end="")\\nsys.exit(0)\\n'
(obj / 'Vt').write_text(model)
(obj / 'Vt').chmod(0o755)
''')
        compiler.chmod(0o755)
        for arguments in (["init", "--quiet"], ["add", "bin"], [
                "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit",
                "--quiet", "-m", "Public gate native fixture"
        ]):
            subprocess.run(["git", *arguments],
                           cwd=self.repository,
                           check=True,
                           capture_output=True)
        self.head = subprocess.check_output(["git", "rev-parse", "HEAD"],
                                            cwd=self.repository,
                                            text=True).strip()
        self.make = self.root / "make.py"
        self.make.write_text(
            "#!/usr/bin/env python3\n# Real native gate fixture; no C++ model build.\n")
        self.make.chmod(0o755)
        self.config = self.root / "config.json"
        self.config.write_text("{}\n")
        self.output = self.root / "out"
        self.environment = dict(os.environ, FINISH_FIXTURE_CONFIG=str(self.config))

    def cli(self, action, expected):
        result = subprocess.run([
            sys.executable,
            str(Path(acceptance.__file__).resolve()), action, "--root",
            str(self.repository), "--expected-head", self.head, "--out",
            str(self.output), "--make",
            str(self.make)
        ],
                                env=self.environment,
                                capture_output=True,
                                text=True,
                                check=False,
                                timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        RECEIPTS.append({
            "test": self.id(),
            "action": action,
            "actual_exit": result.returncode,
            "expected_exit": expected,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "scope": "Native gate fixture; no SV conformance claim"
        })
        return result

    def test_original_case5_literal_and_final_order(self):
        for name, wanted in acceptance.ORIGINAL_SHA256.items():
            self.assertEqual(acceptance.sha(acceptance.ORIGINALS / name), wanted)
        oracle, _ = acceptance.original_functions(acceptance.ORIGINALS / "run_controls_v2.py",
                                                  ["expected", "check", "wave"])
        log = self.root / "model.log"
        log.write_text("OBS 5 before 1\nFINAL 5 1 q=0\n")
        self.assertTrue(oracle["check"](log, 5)["strict_output_passed"])
        log.write_text("OBS 5 before 1\nUNREACHABLE postponed_strobe\nFINAL 5 1 q=1\n")
        self.assertFalse(oracle["check"](log, 5)["strict_output_passed"])
        for name in ("A", "B"):
            log.write_text("OBS 7 before 1\nFINAL 7 " + name + " 1 q=0\n")
            self.assertTrue(oracle["check"](log, 7)["strict_output_passed"])

    def test_zero_exit_wrong_output_propagates_after_all9(self):
        self.cli("run", 1)
        result = self.cli("check", 1)
        audit = json.loads((self.output / "check.json").read_text())
        self.assertEqual((audit["passed"], audit["failed"]), (8, 1))
        self.assertEqual(audit["native_counts"], {
            "compile_exit_0": 9,
            "build_exit_0": 9,
            "run_exit_0": 9
        })
        self.assertEqual(result.stdout.count("FINISH9_CASE "), 9)
        self.assertEqual(result.stdout.count('"wave_complete_utf8"'), 9)
        self.assertIn("UNREACHABLE postponed_strobe", result.stdout)

    def test_early_compile_failure_does_not_omit_later_cases(self):
        self.config.write_text(json.dumps({"compile_fail_case": 0, "wrong_finish5": False}))
        self.cli("run", 1)
        self.cli("check", 1)
        audit = json.loads((self.output / "check.json").read_text())
        self.assertEqual(audit["executed"], 9)
        self.assertEqual(audit["native_counts"]["compile_exit_7"], 1)
        self.assertEqual(audit["native_counts"]["run_exit_0"], 8)
        receipt = json.loads((self.output / "0-initial/compile.finished.json").read_text())
        self.assertEqual((receipt["actual_exit"], receipt["raw_wait_status"]), (7, 1792))

    def test_checker_rejects_changed_actual_log(self):
        self.cli("run", 1)
        with (self.output / "5-nba_postponed/run.log").open("a") as stream:
            stream.write("changed bytes\n")
        result = self.cli("check", 1)
        self.assertIn("receipt/log mismatch", result.stdout)
        self.assertNotIn("FINISH9_AUDIT", result.stdout)

    def test_native_observer_timeout_is_nonzero(self):
        observer = Path(acceptance.__file__).with_name("native_process.py")
        out = self.root / "timeout"
        result = subprocess.run([
            sys.executable,
            str(observer), "--cwd",
            str(self.root), "--out",
            str(out), "--name", "wait", "--timeout", "0.05", "--", sys.executable, "-c",
            "import time;time.sleep(5)"
        ],
                                capture_output=True,
                                check=False,
                                timeout=10)
        self.assertNotEqual(result.returncode, 0)
        receipt = json.loads((out / "wait.finished.json").read_text())
        self.assertEqual(receipt["termination_reason"], "timeout")
        self.assertLess(receipt["actual_exit"], 0)
        RECEIPTS.append({
            "test": self.id(),
            "actual_observer_exit": result.returncode,
            "native_receipt": receipt
        })

    def test_finish_failure_reaches_actual_shell_exit(self):
        source = (acceptance.SOURCE_ROOT / "ci/portable/build.bash").read_text()
        # Include the actual helper and successful gates preceding this isolated tail.
        block = source[source.index("run_evidence() {\n"):]
        block = ("smoke_status=0\nsmoke_record_status=0\nregress_status=0\n"
                 "regression_check_status=0\nevidence_status=0\n"
                 "clocking_wave_status=0\nlegacy_replay_status=0\nlegacy_audit_status=0\n" +
                 block[:block.index("\n}\n") + 3] +
                 source[source.index("icarus_head=$(git rev-parse HEAD)\n"):])
        fake = self.root / "bin"
        fake.mkdir()
        python = fake / "python3"
        python.write_text("#!" + sys.executable + "\n" + '''import json,os,sys
kind = 'finish' if sys.argv[1].endswith('finish_acceptance.py') else 'icarus'
action = sys.argv[2]
if sys.argv[1].endswith('log_evidence.py'):
    print('EVIDENCE_CALLED')
    sys.exit(0)
key = kind + ('_full18' if '--full18' in sys.argv else '_' + action)
print(key.upper() + '_CALLED')
sys.exit(json.loads(os.environ['GATE_FIXTURE_STATUSES']).get(key,0))
''')
        python.chmod(0o755)
        shell = shutil.which("bash")
        for statuses, expected in [({}, 0), ({
                "icarus_full18": 1
        }, 1), ({
                "icarus_full18": 1,
                "finish_run": 1,
                "finish_check": 1
        }, 1), ({
                "icarus_run": 7
        }, 1), ({
                "finish_check": 9
        }, 1)]:
            environment = dict(self.environment,
                               PATH=str(fake) + os.pathsep + os.environ['PATH'],
                               GATE_FIXTURE_STATUSES=json.dumps(statuses),
                               thread_controls_status="0",
                               ram_matrix_status="0")
            result = subprocess.run([shell, "-c", "set -euo pipefail\n" + block],
                                    cwd=self.repository,
                                    env=environment,
                                    text=True,
                                    capture_output=True,
                                    check=False)
            self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
            for marker in ("ICARUS_FULL18_CALLED", "FINISH_RUN_CALLED", "FINISH_CHECK_CALLED",
                           "EVIDENCE_CALLED", "ORIGINAL_ACCEPTANCE_EXITS"):
                self.assertIn(marker, result.stdout)
            RECEIPTS.append({
                "test": self.id(),
                "actual_shell_exit": result.returncode,
                "expected_exit": expected,
                "input_statuses": statuses,
                "stdout": result.stdout,
                "stderr": result.stderr
            })

    def test_original_output_success_can_pass(self):
        self.config.write_text(json.dumps({"wrong_finish5": False}))
        self.cli("run", 0)
        self.cli("check", 0)
        audit = json.loads((self.output / "check.json").read_text())
        self.assertEqual(audit["passed"], 9)
        self.assertEqual(audit["strict_gate_exit"], 0)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(FinishAcceptanceTest)
    suite_result = unittest.TextTestRunner().run(suite)
    output = acceptance.SOURCE_ROOT / "out/finish9-helper-native.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(
        json.dumps(
            {
                "tests_run": suite_result.testsRun,
                "gate_tests_passed": suite_result.wasSuccessful(),
                "native_controls": RECEIPTS,
                "fake_models_do_not_certify_SV_semantics": True
            },
            indent=2) + "\n")
    sys.exit(0 if suite_result.wasSuccessful() else 1)
