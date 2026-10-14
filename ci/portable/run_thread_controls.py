#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Validate real multithreaded execution after the static exec-graph update."""

import json
import re
import subprocess
import sys
from pathlib import Path

from run_regressions import parse_summary, passed_counts

NAMES = ("threads_counter_2", "threads_nondeterminism", "fourstate_mt_trace", "trace_basic_cc_vcd",
         "variable_order_writers")


def main():
    """Require both actual vltmt passes and the original complete summary."""
    root = Path(__file__).resolve().parents[2]
    output = root / "out/thread-controls"
    output.mkdir(parents=True, exist_ok=False)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    command = [
        sys.executable, "driver.py", "--vltmt", "-j2", "--no-skip-identical",
        *["t/t_" + name + ".py" for name in NAMES]
    ]
    result = subprocess.call([
        sys.executable,
        str(root / "ci/portable/native_process.py"), "--cwd",
        str(root / "test_regress"), "--out",
        str(output), "--name", "run", "--timeout", "600", "--min-disk-bytes", "536870912", "--",
        *command
    ])
    text = (output / "run.log").read_text()
    print(text, end="")
    status, counts = parse_summary(text)
    actual = re.findall(r"^vltmt/(t_[A-Za-z0-9_]+): Self PASSED$", text, re.MULTILINE)
    expected = {"t_" + name for name in NAMES}
    passed = (result == 0 and passed_counts(status, counts, len(NAMES))
              and len(actual) == len(set(actual)) == len(NAMES) and set(actual) == expected)
    record = {
        "commit": head,
        "selected": list(NAMES),
        "returncode": result,
        "counts": counts,
        "summary_status": status,
        "actual_pass_names": actual,
        "success": passed
    }
    (output / "results.json").write_text(json.dumps(record, indent=2) + "\n")
    print("THREAD_CONTROLS " + json.dumps(record))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
