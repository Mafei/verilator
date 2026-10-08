#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require recorded regression selections, counts and provenance to agree."""

import json
import subprocess
from pathlib import Path

from run_regressions import GROUPS, parse_summary, passed_counts


def check_results(root):
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    provenance_lines = (root / "out" / "provenance.txt").read_text().splitlines()
    provenance = provenance_lines[0] if provenance_lines else ""
    if head != provenance:
        raise SystemExit("Build provenance does not match the checked-out commit")
    results = json.loads((root / "out" / "regression-results.json").read_text())
    if not isinstance(results, dict) or set(results) != set(GROUPS):
        raise SystemExit("Missing or unexpected regression groups")
    for group, result in results.items():
        selected = GROUPS[group]
        if not isinstance(result, dict):
            raise SystemExit("Malformed regression group: " + group)
        counts = result.get("counts")
        if (not isinstance(counts, dict)
                or any(type(value) is not int
                       for value in counts.values()) or result.get("commit") != head
                or result.get("selected") != selected or type(result.get("expected")) is not int
                or result["expected"] != len(selected) or type(result.get("returncode")) is not int
                or result["returncode"] != 0 or result.get("success") is not True
                or not passed_counts(result.get("summary_status"), counts, len(selected))):
            raise SystemExit("Failed or incomplete regression group: " + group)
        try:
            status, actual_counts = parse_summary(
                (root / "logs" / (group + "-regressions.log")).read_text())
        except (OSError, ValueError) as error:
            raise SystemExit("Missing or invalid regression log: " + group) from error
        if status != result["summary_status"] or actual_counts != counts:
            raise SystemExit("Recorded counts do not match the regression log: " + group)
    print("Verified regression counts for " + head)


def main():
    root = Path(__file__).resolve().parents[2]
    try:
        check_results(root)
    except (OSError, ValueError) as error:
        raise SystemExit("Missing or invalid regression results/provenance") from error


if __name__ == "__main__":
    main()
