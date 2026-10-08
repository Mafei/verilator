#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Print reproducible build evidence without requiring artifact downloads."""

import hashlib
import json
import re
import sys
from pathlib import Path


def compiler_evidence(root):
    """Record the compiler bytes that produced the models and portable package."""
    binary = root / "bin/verilator_bin"
    digest = hashlib.sha256(binary.read_bytes()).hexdigest()
    record = digest + "  bin/verilator_bin\n"
    (root / "out").mkdir(exist_ok=True)
    (root / "out/compiler-SHA256SUMS").write_text(record)
    print("COMPILER_SHA256 " + record, end="")


def enum_evidence(path, root):
    """Normalize only enum type hashes, preserving suffixes and alias identity."""
    raw = path.read_bytes()
    identities = {}

    def replace(match):
        original = match.group(1)
        if original not in identities:
            identities[original] = len(identities)
        return b"__Venum_hHASH" + str(identities[original]).encode("ascii")

    normalized = re.sub(rb"\b__Venum_h([0-9a-f]{8})(?=__\d+\b)", replace, raw)
    return {
        "path":
        str(path.relative_to(root)),
        "raw_sha256":
        hashlib.sha256(raw).hexdigest(),
        "normalized_sha256":
        hashlib.sha256(normalized).hexdigest(),
        "raw_tokens":
        list(
            dict.fromkeys(
                token.decode("ascii")
                for token in re.findall(rb"\b__Venum_h[0-9a-f]{8}__\d+\b", raw))),
        "identities": {
            original.decode("ascii"): "HASH" + str(index)
            for original, index in identities.items()
        }
    }


def results_evidence(root):
    """Print enum records and output hashes, excluding the checksum file itself."""
    paths = sorted((root / "test_regress/obj_vlt/t_debug_emitv").glob("*_width.tree.v"))
    if not paths:
        raise FileNotFoundError("Missing debug enum output")
    records = [enum_evidence(path, root) for path in paths]
    (root / "out").mkdir(exist_ok=True)
    (root / "out/enum-hash-evidence.json").write_text(json.dumps(records, indent=2) + "\n")
    for record in records:
        print("DEBUG_ENUM_EVIDENCE " + json.dumps(record))
    checksum = root / "out/SHA256SUMS"
    files = sorted(path for path in (root / "out").iterdir()
                   if path.is_file() and path != checksum)
    contents = "".join(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name + "\n" for path in files)
    checksum.write_text(contents)
    print("OUTPUT_SHA256SUMS_BEGIN\n" + contents + "OUTPUT_SHA256SUMS_END")


def main():
    """Report the compiler after building or the outputs after validation."""
    if len(sys.argv) != 2 or sys.argv[1] not in ("compiler", "results"):
        raise SystemExit("Usage: log_evidence.py compiler|results")
    root = Path.cwd()
    if sys.argv[1] == "compiler":
        compiler_evidence(root)
    else:
        results_evidence(root)


if __name__ == "__main__":
    main()
