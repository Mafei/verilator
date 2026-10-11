#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run the original nine public finish inputs with their unchanged literal oracles."""
import argparse
import ast
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

SOURCE_ROOT = Path(__file__).resolve().parents[2]
ORIGINALS = Path(__file__).with_name("finish9-original")
ORIGINAL_SHA256 = {
    "finish_controls.sv": "35ad57a486d1efe3f0fdf0749786d812dd7dd4fcba11850529c825a05e92b116",
    "noninline_finish.sv": "eea2731bb6a35154ddcaacac46af24037f4bae49b89fd23dc8265c250e7960d2",
    "run_controls_v2.py": "22b559dad08ad5cbae97b775b3f55dd22a61ef0a5c64721442ae986879ffea22",
    "run_noninline_v2.py": "808586c524cc2665ca75328e1acbbe65e716aa859413ade53241d9923ae70ee3",
}
PROFILES = [
    "initial", "coroutine", "task_caller", "function_caller", "fork_join", "nba_postponed",
    "inactive_future", "final_finish", "independent_callee"
]


def commands(root, output, index, make):
    """Bind each immutable public profile to distinct, freshly created model outputs."""
    case = index if index < 8 else 9
    folder = output / (str(case) + "-" + PROFILES[index])
    obj = folder / "obj"
    definitions = [f"CASE={case}"] if case != 9 else []
    if case in (2, 3, 7):
        definitions.append({2: "FINISH_TASK", 3: "FINISH_FUNCTION", 7: "FINAL_STOP"}[case])
    source = output / "original-inputs" / ("finish_controls.sv"
                                           if case != 9 else "noninline_finish.sv")
    stages = {
        "compile": [
            str(root / "bin/verilator_bin"), "--cc", "--exe", "--main", "--fourstate",
            "-Wno-FUTURE", "--timing", "--trace", "--prefix", "Vt", "--top-module", "t", "--Mdir",
            str(obj), *["+define+" + value for value in definitions],
            str(source)
        ],
        "build": [make, "-C", str(obj), "-f", "Vt.mk", "-j1", "VM_PARALLEL_BUILDS=0"],
        "run": [str(obj / "Vt"), "+verilator+quiet"],
    }
    return case, folder, definitions, source, stages


def sha(path):
    """Hash the actual file bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def original_functions(path, names):
    """Load only oracle functions from the hash-verified immutable public inputs."""
    tree = ast.parse(path.read_text())
    functions = [
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    if {node.name for node in functions} != set(names):
        raise ValueError("missing original oracle function")
    namespace = {"Path": Path, "re": re, "h": SimpleNamespace(sha=sha)}
    assignments = [
        node for node in tree.body if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "expected" for target in node.targets)
    ]
    if assignments:
        namespace["expected"] = ast.literal_eval(assignments[0].value)
    module = ast.Module(body=functions, type_ignores=[])
    # The caller verifies the original public file's complete immutable SHA first.
    exec(compile(module, str(path), "exec"), namespace)  # noqa: S102 # pylint: disable=exec-used
    return namespace, hashlib.sha256(ast.dump(module,
                                              include_attributes=False).encode()).hexdigest()


def collect(args):  # pylint: disable=too-many-locals
    """Execute every profile with fresh outputs before returning the original strict gate."""
    root = args.root.resolve(strict=True)
    head = subprocess.check_output(["git", "--no-optional-locks", "rev-parse", "HEAD"],
                                   cwd=root,
                                   text=True).strip()
    if head != args.expected_head:
        raise ValueError("owned checkout does not match frozen SHA")
    names = list(ORIGINAL_SHA256)
    protected = {name: sha(args.originals / name) for name in names}
    if protected != ORIGINAL_SHA256:
        raise ValueError("original fixture or oracle differs from immutable public manifest")
    control, control_ast_sha = original_functions(args.originals / "run_controls_v2.py",
                                                  ["expected", "check", "wave"])
    noninline, noninline_ast_sha = original_functions(args.originals / "run_noninline_v2.py",
                                                      ["check"])
    args.out.mkdir(parents=True, exist_ok=False)
    inputs = args.out / "original-inputs"
    inputs.mkdir()
    for name in names:
        shutil.copy2(args.originals / name, inputs / name)
    compiler = root / "bin/verilator_bin"
    compiler_sha = sha(compiler)
    observer = Path(__file__).with_name("native_process.py")
    os.environ["VERILATOR_ROOT"] = str(root)
    os.environ["MAKEFLAGS"] = "VM_PARALLEL_BUILDS=0"
    results = []

    def stage(folder, label, command, timeout):
        process = subprocess.run([
            sys.executable,
            str(observer), "--cwd",
            str(folder), "--out",
            str(folder), "--name", label, "--timeout",
            str(timeout), "--", *command
        ],
                                 check=False)
        receipt = json.loads((folder / (label + ".finished.json")).read_text())
        receipt["native_exit"] = receipt["actual_exit"]
        receipt["outer_observer_exit"] = process.returncode
        return receipt

    for index, name in enumerate(PROFILES):
        case, folder, definitions, source, stages = commands(root, args.out, index, args.make)
        folder.mkdir()
        obj = folder / "obj"
        row = {
            "case": case,
            "id": name,
            "source": str(source),
            "source_sha256": sha(source),
            "definitions": definitions
        }
        row["compile"] = stage(folder, "compile", stages["compile"], 60)
        if row["compile"]["actual_exit"] == 0:
            row["build"] = stage(folder, "build", stages["build"], 120)
            if row["build"]["actual_exit"] == 0:
                row["run"] = stage(folder, "run", stages["run"], 15)
                row["binary_sha256"] = sha(obj / "Vt")
                row["check"] = control["check"](
                    row["run"]["log"], case) if case != 9 else noninline["check"](row["run"])
                row["wave"] = control["wave"](folder / "wave.vcd")
        row["gch_count"] = len(list(obj.rglob("*.gch"))) if obj.exists() else 0
        row["strict_passed"] = (
            "run" in row
            and all(row[phase]["actual_exit"] == 0 and row[phase]["termination_reason"] is None
                    for phase in ("compile", "build", "run"))
            and row["check"].get("strict_output_passed", row["check"].get("strict_passed", False)))
        (folder / "result.json").write_text(json.dumps(row, indent=2) + "\n")
        results.append(row)
        print(json.dumps({
            "case": case,
            "id": name,
            "strict_passed": row["strict_passed"],
            "stages": {
                phase: row[phase]["actual_exit"]
                for phase in ("compile", "build", "run") if phase in row
            }
        }),
              flush=True)
    unchanged = protected == {name: sha(args.originals / name) for name in names}
    result = {
        "schema": "unchanged-finish9-frozen-native-v1",
        "commit": head,
        "compiler_physical_sha256": compiler_sha,
        "selected": 9,
        "executed": len(results),
        "NOTRUN": [],
        "passed": sum(row["strict_passed"] for row in results),
        "failed": sum(not row["strict_passed"] for row in results),
        "results": results,
        "original_files_sha256": protected,
        "original_files_unchanged": unchanged,
        "original_oracle_functions_ast_sha256": {
            "controls": control_ast_sha,
            "noninline": noninline_ast_sha
        },
        "golden_modifications": 0,
        "same_region_final_old_value_is_original_boundary_hypothesis": True,
        "compiler_unchanged": sha(compiler) == compiler_sha,
        "strict_gate_exit": int(not unchanged or any(not row["strict_passed"] for row in results))
    }
    (args.out / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result["strict_gate_exit"]


def verify_stage(folder, phase, record, expected_command):
    """Verify actual wait status and immutable log bytes, not a success flag."""
    stored = json.loads((folder / (phase + ".finished.json")).read_text())
    started = json.loads((folder / (phase + ".started.json")).read_text())
    # JSON booleans cannot be PIDs or raw statuses; keep the full rejection gate together.
    # pylint: disable=too-many-boolean-expressions,unidiomatic-typecheck
    if (any(record.get(key) != value for key, value in stored.items())
            or any(stored.get(key) != value for key, value in started.items())
            or stored.get("cwd") != str(folder) or stored.get("argv") != expected_command
            or stored.get("log") != str(folder / (phase + ".log"))
            or type(stored.get("pid")) is not int or stored["pid"] != stored.get("wait4_pid")
            or type(stored.get("raw_wait_status")) is not int
            or stored.get("actual_exit") != os.waitstatus_to_exitcode(stored["raw_wait_status"])
            or stored.get("log_sha256") != sha(stored["log"])
            or stored.get("log_bytes") != Path(stored["log"]).stat().st_size
            or record.get("native_exit") != stored.get("actual_exit")
            or record.get("outer_observer_exit") != (stored["actual_exit"] if stored["actual_exit"]
                                                     >= 0 else 128 - stored["actual_exit"])):
        raise ValueError("Native finish receipt/log mismatch: " + str(folder / phase))
    # pylint: enable=too-many-boolean-expressions,unidiomatic-typecheck
    return stored


def verify(args):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements,too-many-boolean-expressions
    """Recheck all original literal oracles and expose complete model output and VCD."""
    # The rejection gates compare the complete source/receipt contract together.
    # pylint: disable=too-many-boolean-expressions
    root = args.root.resolve(strict=True)
    head = subprocess.check_output(["git", "--no-optional-locks", "rev-parse", "HEAD"],
                                   cwd=root,
                                   text=True).strip()
    result = json.loads((args.out / "summary.json").read_text())
    if (head != args.expected_head or result.get("commit") != head
            or result.get("compiler_physical_sha256") != sha(root / "bin/verilator_bin") or {
                name: sha(args.originals / name)
                for name in ORIGINAL_SHA256
            } != ORIGINAL_SHA256 or {
                name: sha(args.out / "original-inputs" / name)
                for name in ORIGINAL_SHA256
            } != ORIGINAL_SHA256 or result.get("original_files_sha256") != ORIGINAL_SHA256
            or result.get("golden_modifications") != 0
            or result.get("original_files_unchanged") is not True
            or result.get("compiler_unchanged") is not True):
        raise ValueError("Finish compiler/source/original-input provenance mismatch")
    control, control_sha = original_functions(args.originals / "run_controls_v2.py",
                                              ["expected", "check", "wave"])
    noninline, noninline_sha = original_functions(args.originals / "run_noninline_v2.py",
                                                  ["check"])
    if result.get("original_oracle_functions_ast_sha256") != {
            "controls": control_sha,
            "noninline": noninline_sha
    }:
        raise ValueError("Original finish oracle function mismatch")
    rows = result.get("results", [])
    if (len(rows) != 9 or [row.get("id") for row in rows] != PROFILES
            or [row.get("case")
                for row in rows] != list(range(8)) + [9] or result.get("selected") != 9
            or result.get("executed") != 9 or result.get("NOTRUN") != []):
        raise ValueError("Missing, duplicate or unrun original finish profile")
    passed, counts, pids = 0, {}, []
    for index, row in enumerate(rows):
        case = row["case"]
        _, folder, definitions, source, stages = commands(root, args.out, index, args.make)
        if (row.get("source") != str(source) or row.get("source_sha256") != sha(source)
                or row.get("definitions") != definitions):
            raise ValueError("Finish case source or definitions differ")
        if json.loads((folder / "result.json").read_text()) != row:
            raise ValueError("Finish case differs from saved row")
        for phase in ("compile", "build", "run"):
            if phase in row:
                stored = verify_stage(folder, phase, row[phase], stages[phase])
                pids.append(stored["pid"])
                key = phase + "_exit_" + str(stored["actual_exit"])
                counts[key] = counts.get(key, 0) + 1
                if stored["termination_reason"] is not None:
                    counts["terminated"] = counts.get("terminated", 0) + 1
        observed = {
            "case": case,
            "id": row["id"],
            "strict_passed": False,
            "stages": {
                phase: row[phase]
                for phase in ("compile", "build", "run") if phase in row
            }
        }
        if "run" in row:
            check = control["check"](row["run"]["log"], case) if case != 9 else noninline["check"](
                row["run"])
            wave = control["wave"](folder / "wave.vcd")
            if (row.get("check") != check or row.get("wave") != wave
                    or row.get("binary_sha256") != sha(folder / "obj/Vt")):
                raise ValueError("Original literal finish output/wave/model hash mismatch")
            observed["full_raw_output_utf8"] = Path(row["run"]["log"]).read_text(encoding="utf-8")
            observed["check"] = check
            observed["wave"] = wave
            if wave["present"]:
                raw = (folder / "wave.vcd").read_bytes()
                observed["wave_complete_utf8"] = raw.decode("utf-8")
                observed["wave_bytes"] = len(raw)
            observed["strict_passed"] = (all(phase in row and row[phase]["actual_exit"] == 0
                                             and row[phase]["termination_reason"] is None
                                             for phase in ("compile", "build", "run"))
                                         and check.get("strict_output_passed",
                                                       check.get("strict_passed", False)))
        if observed["strict_passed"] != row.get("strict_passed"):
            raise ValueError("Finish semantic result differs from original oracle")
        passed += observed["strict_passed"]
        print("FINISH9_CASE " + json.dumps(observed), flush=True)
    gate = int(passed != 9)
    if (len(pids) != len(set(pids)) or result.get("passed") != passed
            or result.get("failed") != 9 - passed or result.get("strict_gate_exit") != gate):
        raise ValueError("Finish counts or original strict gate mismatch")
    audit = {key: value for key, value in result.items() if key != "results"}
    audit.update(actual_receipts_logs_original_oracles_verified=True,
                 native_counts=counts,
                 summary_sha256=sha(args.out / "summary.json"),
                 output_filtering="NONE; original literal owned-lines and forbidden-lines oracle",
                 case5_normative_certification=False)
    check_path = args.out / "check.json"
    with check_path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(audit, indent=2) + "\n")
    print("FINISH9_AUDIT " + json.dumps(audit), flush=True)
    return gate
    # pylint: enable=too-many-boolean-expressions


def main():
    """Run all nine cases or independently check their original expected output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["run", "check"])
    parser.add_argument("--root", type=Path, default=SOURCE_ROOT)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--out", type=Path, default=SOURCE_ROOT / "out/finish9")
    parser.add_argument("--originals", type=Path, default=ORIGINALS)
    parser.add_argument("--make", default="make")
    args = parser.parse_args()
    args.root = args.root.resolve(strict=True)
    args.out = args.out.resolve()
    args.originals = args.originals.resolve(strict=True)
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        return collect(args) if args.action == "run" else verify(args)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print("Original finish9 acceptance rejected: " + str(error), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
