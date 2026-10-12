#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Print reproducible build evidence without requiring artifact downloads."""

import hashlib
import json
import re
import sys
from pathlib import Path

CONTROLS_WAVE_BUDGET = 512 * 1024


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


def semantic_wave_evidence(root):
    """Print all bytes of the public semantic fixtures within a hard budget."""
    fixtures = ("t_fourstate_nba_event_concat", "t_fourstate_packed_port_kind",
                "t_timing_nba_event_concat", "t_timing_blocking_event",
                "t_fourstate_blocking_event", "t_fourstate_force_release",
                "t_force_packed_release")
    base = root / "test_regress/obj_vlt"
    collections = [(fixture, base / fixture) for fixture in fixtures]
    wave_evidence(root, collections, "semantic-wave-evidence.json", "SEMANTIC_WAVE_BYTES",
                  128 * 1024)


def finish_wave_evidence(root):
    """Print every deterministic finish profile's complete wave bytes."""
    base = root / "test_regress/obj_vlt"
    fixtures = ("t_timing_finish_boundary", "t_fourstate_finish_boundary")
    collections = [(fixture + "/case" + str(case), base / fixture / ("case" + str(case)))
                   for fixture in fixtures for case in range(10)]
    for fixture, directory in collections:
        paths = sorted(directory.glob("*.vcd"))
        if len(paths) != 1 or paths[0].name != "simx.vcd":
            raise ValueError("Missing or unexpected finish VCD: " + fixture)
    wave_evidence(root, collections, "finish-wave-evidence.json", "FINISH_WAVE_BYTES", 64 * 1024)


def controls_wave_evidence(root):
    """Require nine flat controls and every array, API, and trace profile."""
    root = root.resolve()
    base = root / "test_regress/obj_vlt"
    fixtures = ("t_fourstate_port_init", "t_fourstate_port_partial", "t_fourstate_port_static",
                "t_fourstate_nba_capture", "t_fourstate_nba_race", "t_fourstate_nba_tasks",
                "t_fourstate_nba_trigger", "t_fourstate_nba_unknown", "t_fourstate_array_guard")
    collections = [(fixture, base / fixture) for fixture in fixtures]
    expected = {fixture: {base / fixture / "simx.vcd"} for fixture in fixtures}
    profiled = (("t_fourstate_array_init", ("width7", "width33", "width65")),
                ("t_fourstate_port_api", ("default", "on", "off")), ("t_fourstate_trace_resume",
                                                                     ("two_state", "four_state")))
    for fixture, profiles in profiled:
        collections += [(fixture + "/" + profile, base / fixture / profile)
                        for profile in profiles]
        expected[fixture] = {base / fixture / profile / "simx.vcd" for profile in profiles}
    for fixture, wanted in expected.items():
        directory = base / fixture
        for ancestor in (base.parent, base, directory):
            if ancestor.is_symlink():
                raise ValueError("Symlinked control fixture: " + fixture)
        if not directory.is_dir():
            raise ValueError("Missing or unexpected control VCD: " + fixture)
        for path in directory.rglob("*"):
            if path.is_symlink() and (path.suffix == ".vcd" or path.is_dir()):
                raise ValueError("Symlinked control output: " + str(path))
        if set(directory.rglob("*.vcd")) != wanted:
            raise ValueError("Missing or unexpected control VCD: " + fixture)
    wave_evidence(root,
                  collections,
                  "controls-wave-evidence.json",
                  "CONTROLS_WAVE_BYTES",
                  CONTROLS_WAVE_BUDGET,
                  require_complete=True)


def wave_evidence(root, collections, filename, prefix, budget, require_complete=False):
    """Emit regular public wave files with bounded size and exact byte hashes."""
    total = 0
    records = []
    for fixture, directory in collections:
        if directory.is_symlink() or not directory.resolve().is_relative_to(root.resolve()):
            raise ValueError("Symlinked semantic fixture: " + fixture)
        paths = sorted(directory.glob("*.vcd"))
        if not paths:
            raise FileNotFoundError("Missing semantic VCD: " + fixture)
        for path in paths:
            if path.is_symlink() or not path.is_file():
                raise ValueError("Nonregular semantic VCD: " + str(path))
            size = path.stat().st_size
            if not size or total + size > budget:
                raise ValueError("Empty or oversized semantic VCD collection")
            with path.open("rb") as stream:
                raw = stream.read(budget - total + 1)
            total += len(raw)
            if len(raw) != size or total > budget:
                raise ValueError("Empty or oversized semantic VCD collection")
            if require_complete and (
                    not raw.endswith(b"\n") or not re.search(rb"(?m)^[ \t]*\$var[ \t]", raw)
                    or not re.search(rb"(?m)^[ \t]*\$enddefinitions[ \t]+\$end[ \t]*\r?$", raw)
                    or not re.search(rb"(?m)^#[0-9]+[ \t]*\r?$", raw)):
                raise ValueError("Incomplete control VCD: " + str(path))
            records.append({
                "fixture": fixture,
                "path": str(path.relative_to(root)),
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "contents_utf8": raw.decode("utf-8")
            })
    evidence = {"total_bytes": total, "budget_bytes": budget, "records": records}
    (root / "out").mkdir(exist_ok=True)
    (root / "out" / filename).write_text(json.dumps(evidence, indent=2) + "\n")
    print(prefix + " " + json.dumps(evidence))


def main():
    """Report the compiler after building or the outputs after validation."""
    if len(sys.argv) != 2 or sys.argv[1] not in ("compiler", "results", "semantic-waves",
                                                 "finish-waves", "controls-waves"):
        raise SystemExit(
            "Usage: log_evidence.py compiler|results|semantic-waves|finish-waves|controls-waves")
    root = Path.cwd()
    if sys.argv[1] == "compiler":
        compiler_evidence(root)
    elif sys.argv[1] == "results":
        results_evidence(root)
    elif sys.argv[1] == "semantic-waves":
        semantic_wave_evidence(root)
    elif sys.argv[1] == "finish-waves":
        finish_wave_evidence(root)
    else:
        controls_wave_evidence(root)


if __name__ == "__main__":
    main()
