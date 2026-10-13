#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run the original public six-lane RAM matrix and its complete-history oracle."""

import json
import subprocess
import sys
from pathlib import Path


def run_stage(root, output, name, command, timeout):
    """Keep each actual command, wait status and complete log in its own receipt."""
    return subprocess.call([
        sys.executable,
        str(root / "ci/portable/native_process.py"), "--cwd",
        str(output), "--out",
        str(output), "--name", name, "--timeout",
        str(timeout), "--min-disk-bytes", "536870912", "--", *command
    ])


def main():
    """Reject any failed original stage before accepting the unchanged oracle."""
    root = Path(__file__).resolve().parents[2]
    output = root / "out/ram-matrix/original"
    output.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    source = root / "ci/portable/ram-matrix-original/matrix.v"
    objects = output / "obj"
    compile_command = [
        str(root / "bin/verilator_bin"), "--cc", "--exe", "--main", "--timing", "--trace",
        "--fourstate", "-Wno-FUTURE", "--debug-check", "--output-split", "10000",
        "--output-split-cfuncs", "50", "--Mdir",
        str(objects), "--prefix", "Vt", "--top-module", "t",
        str(source)
    ]
    stages = [("compile", compile_command, 120),
              ("build", ["make", "-C", str(objects), "-f", "Vt.mk", "-j2"], 120),
              ("run", [str(objects / "Vt")], 30)]
    for name, command, timeout in stages:
        result = run_stage(root, output, name, command, timeout)
        if result:
            print("RAM_MATRIX_STAGE_FAILED " + json.dumps({
                "commit": head,
                "stage": name,
                "returncode": result
            }))
            return result
    command = [
        sys.executable,
        str(root / "ci/portable/ram-matrix-original/verify_matrix.py"), "--log",
        str(output / "run.log"), "--vcd",
        str(output / "t_fourstate_array_tmp.vcd"), "--evidence",
        str(output), "--output",
        str(output / "oracle.json"), "--label", head
    ]
    result = run_stage(root, output, "check", command, 30)
    print("RAM_MATRIX_CHECK_EXIT " + json.dumps({"commit": head, "returncode": result}))
    if not result:
        print((output / "check.log").read_text(), end="")
    return result


if __name__ == "__main__":
    sys.exit(main())
