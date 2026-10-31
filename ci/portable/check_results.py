#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require recorded regression selections, counts and provenance to agree."""

import hashlib
import json
import subprocess
from pathlib import Path

import clocking_legacy
from run_regressions import GROUPS, parse_summary, passed_counts, passed_names, selection_revision


def clocking_evidence(root, head):
    """Require freshly audited legacy failures bound to this compiler and commit."""
    report = clocking_legacy.audit(root, root / 'out/clocking-legacy')
    binary = hashlib.sha256((root / 'bin/verilator_bin').read_bytes()).hexdigest()
    if (report['head'] != head or report['compiler_checkout_head'] != head
            or report['compiler_matches_run_head'] is not True
            or report['compiler_sha256'] != binary):
        raise ValueError('Legacy compiler or checkout provenance mismatch')
    return {
        'schema': 'portable-clocking-legacy-evidence-v1',
        'selection_revision': selection_revision(),
        'legacy': clocking_legacy.core_fields(report),
    }


def check_results(root):
    """Require every selected group to agree with its log and build commit."""
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    provenance_lines = (root / "out" / "provenance.txt").read_text().splitlines()
    provenance = provenance_lines[0] if provenance_lines else ""
    if head != provenance:
        raise SystemExit("Build provenance does not match the checked-out commit")
    results = json.loads((root / "out" / "regression-results.json").read_text())
    if not isinstance(results, dict) or set(results) != set(GROUPS):
        raise SystemExit("Missing or unexpected regression groups")
    selected_names = [name for names in GROUPS.values() for name in names]
    if len(selected_names) != len(set(selected_names)):
        raise SystemExit("Regression groups select duplicate test names")
    clocking_evidence(root, head)
    for group, result in results.items():
        selected = GROUPS[group]
        if not isinstance(result, dict):
            raise SystemExit("Malformed regression group: " + group)
        counts = result.get("counts")
        # JSON booleans must not pass integer checks through isinstance(). Keep
        # the full rejection gate together so its strict requirements are clear.
        # pylint: disable=too-many-boolean-expressions,unidiomatic-typecheck
        if (not isinstance(counts, dict)
                or any(type(value) is not int
                       for value in counts.values()) or result.get("commit") != head
                or result.get("selected") != selected or type(result.get("expected")) is not int
                or result["expected"] != len(selected) or type(result.get("returncode")) is not int
                or result["returncode"] != 0 or result.get("success") is not True
                or not passed_counts(result.get("summary_status"), counts, len(selected))):
            raise SystemExit("Failed or incomplete regression group: " + group)
        # pylint: enable=too-many-boolean-expressions,unidiomatic-typecheck
        try:
            log_text = (root / "logs" / (group + "-regressions.log")).read_text()
            status, actual_counts = parse_summary(log_text)
        except (OSError, ValueError) as error:
            raise SystemExit("Missing or invalid regression log: " + group) from error
        if status != result["summary_status"] or actual_counts != counts:
            raise SystemExit("Recorded counts do not match the regression log: " + group)
        if not passed_names(log_text, selected):
            raise SystemExit("Passed test names do not match the selected drivers: " + group)
    print("Verified regression counts for " + head)


def main():
    """Check results in this checkout, reporting missing inputs as failures."""
    root = Path(__file__).resolve().parents[2]
    try:
        check_results(root)
    except (OSError, ValueError) as error:
        raise SystemExit("Missing or invalid regression results/provenance") from error


if __name__ == "__main__":
    main()
