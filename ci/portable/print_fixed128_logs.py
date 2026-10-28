#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Print existing fixed128 producer evidence; never execute models or change gates.

Exit zero means the printed evidence is consistent, not that its semantic gate
passed. Exit two means missing, partial, or inconsistent producer evidence.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys

PIN = "f45ffabed3212a106f01cb362ef42c5d293f4513"
INVENTORY_SHA = "d90ada099b8aff78e164a2a70889b170200859cd6d8b90d084497dbb6f21d347"
SELECTION_SHA = "ce063b8824b930198819261c44265c5b6e6cc2d865b9221b736c511e685c7827"
STAGES = ("compile", "build", "run", "oracle")


def emit(marker, value):
    """Escape newlines and annotations inside source/tool text."""
    print(marker + " " + json.dumps(value, sort_keys=True, ensure_ascii=True), flush=True)


def bounded(root, relative):
    """Read only known relative files under an explicitly supplied local root."""
    relative = PurePosixPath(relative)
    if relative.is_absolute() or not relative.parts or any(part in (".", "..") or "\\" in part
                                                           for part in relative.parts):
        raise ValueError("invalid relative evidence path")
    path = root
    for part in relative.parts:
        path = path / part
        if path.is_symlink():
            raise ValueError("evidence symlink is not permitted: " + str(relative))
    return path


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            value.update(chunk)
    return {"bytes": path.stat().st_size, "sha256": value.hexdigest()}


def excerpt(path, limit):
    """Show bounded raw head/tail bytes; full-byte digest is printed separately."""
    size = path.stat().st_size
    with path.open("rb") as stream:
        head = stream.read(limit if size <= limit else limit // 2)
        stream.seek(max(len(head), size - limit // 2))
        tail = stream.read(limit - len(head))
    return {
        "head_utf8": head.decode("utf-8", errors="replace"),
        "tail_utf8": tail.decode("utf-8", errors="replace"),
        "raw_bytes_omitted": size - len(head) - len(tail),
        "truncated": size > limit
    }


def stage_record(pair, recorded_pair, index, engine, name, record, show_output, limit):
    relative = f"cases/{index:04d}/{engine}/{name}"
    receipt_path = bounded(pair, relative + ".finished.json")
    receipt = read_json(receipt_path)
    fields = ("actual_exit", "raw_wait_status", "pid", "wait4_pid", "termination_reason", "argv",
              "log", "log_bytes", "log_sha256")
    if any(receipt.get(key) != record.get(key) for key in fields):
        raise ValueError("native receipt differs from result: " + relative)
    if (record["argv"][4:6] != [record["stdout"], record["stderr"]]
            or record["argv"][6:] != record["invoked_argv"]):
        raise ValueError("native launcher/command mismatch: " + relative)
    actual, raw = record["actual_exit"], record["raw_wait_status"]
    if (type(actual) is not int or type(raw) is not int or os.waitstatus_to_exitcode(raw) != actual
            or record["pid"] != record["wait4_pid"]
            or record["observer_exit"] != (actual if actual >= 0 else 128 - actual)):
        raise ValueError("native wait/observer mismatch: " + relative)
    streams = {}
    for label, suffix in (("log", ".log"), ("stdout", ".stdout"), ("stderr", ".stderr"),
                          ("output_log", ".output.log")):
        # Recorded absolute paths are compared only, never opened. This maps the
        # Rocky /source prefix to the already mounted local --pair directory.
        if record[label] != str(recorded_pair / (relative + suffix)):
            raise ValueError("recorded path mismatch: " + relative + suffix)
        path = bounded(pair, relative + suffix)
        value = digest(path)
        if (value["sha256"] != record[label + "_sha256"]
                or label != "output_log" and value["bytes"] != record[label + "_bytes"]):
            raise ValueError("stream digest mismatch: " + relative + suffix)
        streams[label] = value
        if show_output and label == "output_log":
            value["excerpt"] = excerpt(path, limit)
    return {
        **{
            key: record[key]
            for key in fields if key not in ("argv", "log")
        }, "observer_exit": record["observer_exit"],
        "invoked_argv": record["invoked_argv"],
        "receipt": digest(receipt_path),
        "streams_rehashed": streams
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pair", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--select", required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--excerpt-bytes", type=int, default=2048)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}",
                        args.expected_head) or not 128 <= args.excerpt_bytes <= 8192:
        parser.error("require a full SHA and an excerpt limit of 128..8192 bytes")
    pair = args.pair.resolve(strict=True)
    source = args.source.resolve(strict=True)
    inventory_path = args.inventory.resolve(strict=True)
    selection_path = args.select.resolve(strict=True)
    if (digest(inventory_path)["sha256"] != INVENTORY_SHA
            or digest(selection_path)["sha256"] != SELECTION_SHA):
        raise ValueError("original inventory/selection digest mismatch")
    inventory = read_json(inventory_path)
    selected = read_json(selection_path)["scenario_ids"]
    by_id = {row["scenario_id"]: row for row in inventory}
    binding = read_json(bounded(pair, "binding.json"))
    if (len(inventory) != 3850 or len(by_id) != 3850 or len(selected) != 128
            or len(set(selected)) != 128 or binding["verilator_commit"] != args.expected_head
            or binding["icarus_commit"] != PIN or binding["inventory_sha256"] != INVENTORY_SHA
            or binding["selection_sha256"] != SELECTION_SHA):
        raise ValueError("fixed128 identity/binding mismatch")
    recorded_version = PurePosixPath(binding["version"]["stdout"])
    if (not recorded_version.is_absolute() or recorded_version.name != "version.stdout"
            or ".." in recorded_version.parts or "\\" in str(recorded_version)):
        raise ValueError("invalid recorded pair root")
    recorded_pair = recorded_version.parent
    top_path = bounded(pair, "results.json")
    top = read_json(top_path) if top_path.exists() else None
    if top and top["binding"] != binding:
        raise ValueError("top-level binding differs")
    emit(
        "FIXED128_LOG_HEADER", {
            "scope": "PRODUCER_FILES_REHASHED_BEFORE_UPLOAD",
            "not_artifact_zip_verification": True,
            "head": args.expected_head,
            "icarus_pin": PIN,
            "inventory": digest(inventory_path),
            "selection": digest(selection_path),
            "binding": digest(bounded(pair, "binding.json")),
            "recorded_pair": str(recorded_pair),
            "local_pair": str(pair),
            "compiler_sha256_recorded": binding["tools"]["verilator_bin"]["sha256"]
        })
    counts, errors, completed = Counter(), [], 0
    for index, sid in enumerate(selected):
        projected = {"index": index, "scenario_id": sid, "head": args.expected_head}
        try:
            case_path = bounded(pair, f"cases/{index:04d}/result.json")
            if not case_path.exists():
                projected["pair_status"] = "UNRUN"
            else:
                row = read_json(case_path)
                contract_path = bounded(pair, f"cases/{index:04d}/original-contract.json")
                contract = read_json(contract_path)
                if (row["scenario_id"] != sid or contract != by_id[sid]
                        or top and top["results"][index] != row):
                    raise ValueError("case/contract/top-level row mismatch")
                original_path = bounded(source, contract["source"]["path"])
                original = digest(original_path)
                if (original["sha256"] != contract["source"]["sha256"]
                        or original["bytes"] != contract["source"]["bytes"]):
                    raise ValueError("original case source digest mismatch")
                projected.update(pair_status=row["pair_status"],
                                 case_result=digest(case_path),
                                 contract=digest(contract_path),
                                 source={
                                     **contract["source"], "rehashed": original
                                 },
                                 engines={})
                for engine in ("icarus", "verilator"):
                    value = row[engine]
                    if set(value["stages"]) - set(STAGES):
                        raise ValueError("unknown native stage")
                    projected["engines"][engine] = {
                        "status": value["status"],
                        "runtime_executed": value["runtime_executed"],
                        "original_oracle_accepted": value["original_oracle_accepted"],
                        "stages": {}
                    }
                    for name in STAGES:
                        record = value["stages"].get(name)
                        printed = {"execution": "NOT_EXECUTED"}
                        if record:
                            printed = stage_record(pair, recorded_pair, index, engine, name,
                                                   record, row["pair_status"] != "PASS_BOTH",
                                                   args.excerpt_bytes)
                        projected["engines"][engine]["stages"][name] = printed
                    if "oracle" in value["stages"]:
                        filename = ("original-oracle-input.log"
                                    if contract["family"] == "perl-vvp" else "run.stdout")
                        relative = f"cases/{index:04d}/{engine}/{filename}"
                        oracle_input = bounded(pair, relative)
                        if not oracle_input.exists():
                            raise ValueError("missing original oracle input")
                        if value["stages"]["oracle"]["invoked_argv"][-1] != str(recorded_pair /
                                                                                relative):
                            raise ValueError("original oracle input path mismatch")
                        projected["engines"][engine]["original_oracle_input_rehashed"] = {
                            "relative_path": relative,
                            **digest(oracle_input)
                        }
                completed += 1
            counts[projected["pair_status"]] += 1
        except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
            projected["log_integrity_error"] = str(error)
            errors.append({"index": index, "scenario_id": sid, "error": str(error)})
        emit("FIXED128_CASE", projected)
    summary = top["summary"] if top else None
    if (not summary or completed != 128 or len(top["results"]) != 128
            or summary["pair_status_counts"] != dict(counts) or summary["completed"] != 128
            or summary["selected"] != 128 or summary["selected_unrun"] != 0
            or summary["unselected_UNRUN"] != 3722):
        errors.append({"error": "missing, partial, or inconsistent final128 summary"})
    emit(
        "FIXED128_LOG_END", {
            "head": args.expected_head,
            "selected": 128,
            "completed_and_rehashed": completed,
            "counts": dict(counts),
            "recorded_semantic_summary": summary,
            "log_integrity_errors": errors,
            "log_projection_exit": 2 if errors else 0,
            "semantic_gate_unchanged": True,
            "zip_bytes_not_downloaded": True
        })
    return 2 if errors else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        emit("FIXED128_LOG_UNAVAILABLE", {
            "error": str(error),
            "log_projection_exit": 2,
            "semantic_acceptance_claimed": False
        })
        sys.exit(2)
