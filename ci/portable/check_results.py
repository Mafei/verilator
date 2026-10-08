#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require recorded regression selections, counts and provenance to agree."""

import json
from pathlib import Path
import subprocess

from run_regressions import GROUPS


def main():
    root = Path(__file__).resolve().parents[2]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                   text=True).strip()
    provenance = (root / "out" / "provenance.txt").read_text().splitlines()[0]
    if head != provenance:
        raise SystemExit("Build provenance does not match the checked-out commit")
    results = json.loads((root / "out" / "regression-results.json").read_text())
    if not results:
        raise SystemExit("Missing regression groups")
    for group, result in results.items():
        selected = GROUPS[group]
        counts = result["counts"]
        if (result["selected"] != selected or result["expected"] != len(selected)
                or result["returncode"] != 0 or not result["success"]
                or counts.get("passed") != len(selected)
                or counts.get("failed") != 0 or counts.get("skipped", 0) != 0):
            raise SystemExit("Failed or incomplete regression group: " + group)
    print("Verified regression counts for " + head)


if __name__ == "__main__":
    main()
