#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Report the reviewed case122 conflict without changing original pair gates."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

import print_fixed128_logs as fixed
from run_regressions import GROUPS, parse_summary, passed_counts, passed_names

SID = "python-default:0557:sv_queue_min_max_with"
NAME = "fourstate_queue_projection"
GROUP = "sv_semantics_20261026"
SOURCE = "ivtest/ivltests/sv_queue_min_max_with.v"
SOURCE_SHA = "d38c4c95209e986823e04e9ae983269b7d4f0c9fe28d78f86c79b869b73fa68f"
CONFIG = "ivtest/vvp_tests/sv_queue_min_max_with.json"
CONFIG_SHA = "10aa3e0a30cfb6c0ade0105feca2ab04a9fbaea13964f39a0e17906b9d6281bd"
ORACLE = "ivtest/run_ivl.py"
ORACLE_SHA = "5abe0f1a3b8ccb3b6d48fad254b4d1d2fe8745d8993ce932e6e27464370e688f"
INVENTORY_SHA = fixed.INVENTORY_SHA
SELECTION_SHA = fixed.SELECTION_SHA
FLAGS = ["-g2005-sv", "-D__ICARUS_UNSIZED__"]
ORACLE_PROGRAM = ("import json,sys,run_ivl; options=json.loads(sys.argv[1]); "
                  "output=open(sys.argv[2],encoding='ascii').read(); "
                  "result=run_ivl.check_run_outputs(options,output,[],False); "
                  "print(json.dumps(result)); sys.exit(result[0])")
PARSER_FIELDS = {
    "diff": None,
    "gold": None,
    "iverilog_args": FLAGS,
    "key": "sv_queue_min_max_with",
    "modulename": None,
    "source": "ivltests/sv_queue_min_max_with.v",
    "type": "normal",
    "vvp_args": [],
    "vvp_args_extended": []
}


def require(condition, reason):
    """Reject incomplete or inconsistent evidence even with optimized Python."""
    if not condition:
        raise ValueError(reason)


def sha(path):
    return fixed.digest(path)["sha256"]


def read(path):
    return fixed.read_json(path)


def git_bytes(root, head, relative):
    """Bind the standard regression's actual bytes to the requested commit."""
    return subprocess.check_output(["git", "-C", str(root), "show", head + ":" + relative])


def standard(root, head, standard_root=None, regression_root=None):
    """Use checked harness execution and runtime assertions, not pickle or badge."""
    result = {
        "status": "PASS",
        "checks_per_profile": 100,
        "profiles": ["two", "four"],
        "raw_wait_status": "NOT_RECORDED",
        "scope": "harness_checked_return_and_assertions"
    }
    for suffix, field in [("v", "source_sha256"), ("py", "driver_sha256")]:
        rel = "test_regress/t/t_" + NAME + "." + suffix
        content = git_bytes(root, head, rel)
        require(fixed.bounded(root, rel).read_bytes() == content, "standard_source_not_committed")
        result[field] = hashlib.sha256(content).hexdigest()
    regression_root = root if regression_root is None else regression_root.resolve(strict=True)
    profile_root = (fixed.bounded(root, "test_regress/obj_vlt/t_" +
                                  NAME) if standard_root is None else standard_root.resolve(
                                      strict=True))
    groups = read(fixed.bounded(regression_root, "out/regression-results.json"))
    row = groups[GROUP]
    require(
        row["commit"] == head and row["selected"] == GROUPS[GROUP]
        and row["selected"].count(NAME) == 1 and row["expected"] == len(GROUPS[GROUP]),
        "standard_group_identity_mismatch")
    text = fixed.bounded(regression_root, "logs/" + GROUP + "-regressions.log").read_text()
    status, counts = parse_summary(text)
    require(status == row["summary_status"] and counts == row["counts"],
            "standard_group_summary_mismatch")
    require(
        type(row["returncode"]) is int and type(row["success"]) is bool
        and type(row["expected"]) is int
        and all(type(value) is int for value in row["counts"].values()) and row["success"]
        == (row["returncode"] == 0 and passed_counts(status, counts, len(GROUPS[GROUP]))
            and passed_names(text, GROUPS[GROUP])), "standard_group_result_inconsistent")
    require(
        len(re.findall(r"^vlt/t_" + NAME + r": Self PASSED$", text, re.M)) == 1,
        "standard_driver_not_passed_once")
    result["logs_sha256"] = []
    for profile in result["profiles"]:
        path = fixed.bounded(profile_root, profile + "/run.log")
        text = path.read_text()
        require(
            re.findall(r"^Queue projection checks: (\d+)$", text, re.M) == ["100"]
            and text.count("*-* All Finished *-*") == 1
            and not re.search(r"%Error|ERROR:|Aborting|FAILED", text),
            "standard_runtime_failed_or_incomplete")
        result["logs_sha256"].append(sha(path))
    return result


def collect(root,
            pair,
            source,
            inventory_path,
            selection_path,
            head,
            standard_root=None,
            regression_root=None):
    """Review only the approved pinned input; retain every original failure."""
    require(re.fullmatch(r"[0-9a-f]{40}", head), "full_head_required")
    require(
        subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                text=True).strip() == head, "checkout_head_mismatch")
    require(
        sha(inventory_path) == INVENTORY_SHA and sha(selection_path) == SELECTION_SHA,
        "original_inventory_or_selection_changed")
    inventory = read(inventory_path)
    selected = read(selection_path)["scenario_ids"]
    by_id = {x["scenario_id"]: x for x in inventory}
    require(
        len(inventory) == len(by_id) == 3850 and len(selected) == len(set(selected)) == 128
        and selected.count(SID) == 1 and all(sid in by_id for sid in selected),
        "original_selection_invalid")
    index = selected.index(SID)
    contract = read(fixed.bounded(pair, f"cases/{index:04d}/original-contract.json"))
    require(
        contract == by_id[SID] and contract["source"]["path"] == SOURCE
        and contract["source"]["bytes"] == 780 and contract["source"]["sha256"] == SOURCE_SHA
        and contract["family"] == "python-vvp" and contract["effective_type"] == "normal"
        and contract["effective_oracle"] == "selfchecking_passed_line"
        and contract["oracle"] == ORACLE and contract["iverilog_args"] == FLAGS
        and contract["parser_fields"] == PARSER_FIELDS, "case122_original_contract_changed")
    for rel, expected in [(SOURCE, SOURCE_SHA), (CONFIG, CONFIG_SHA), (ORACLE, ORACLE_SHA)]:
        require(sha(fixed.bounded(source, rel)) == expected, "case122_original_bytes_changed")
    binding = read(fixed.bounded(pair, "binding.json"))
    require(
        binding["verilator_commit"] == head and binding["icarus_commit"] == fixed.PIN
        and binding["inventory_sha256"] == INVENTORY_SHA
        and binding["selection_sha256"] == SELECTION_SHA, "pair_binding_mismatch")
    compiler_sha = sha(fixed.bounded(root, "bin/verilator_bin"))
    require(binding["tools"]["verilator_bin"]["sha256"] == compiler_sha,
            "pair_compiler_bytes_mismatch")
    recorded = PurePosixPath(binding["version"]["stdout"])
    require(
        recorded.is_absolute() and recorded.name == "version.stdout" and ".." not in recorded.parts
        and "\\" not in str(recorded), "pair_root_invalid")
    recorded = recorded.parent
    top = read(fixed.bounded(pair, "results.json"))
    row = read(fixed.bounded(pair, f"cases/{index:04d}/result.json"))
    require(
        top["binding"] == binding and [x["scenario_id"] for x in top["results"]] == selected
        and top["results"][index] == row and row["scenario_id"] == SID
        and row["pair_status"] == "UNREVIEWED_OUTPUT_DIFFERENCE", "original_pair_changed")
    counts = dict(Counter(x["pair_status"] for x in top["results"]))
    reported_counts = top["summary"]["pair_status_counts"]
    require(
        isinstance(reported_counts, dict)
        and all(type(value) is int for value in reported_counts.values())
        and type(top["summary"]["batch_gate_exit"]) is int and reported_counts == counts
        and top["summary"]["batch_gate_exit"] == 1
        and top["summary"]["protected_inputs_and_tools_unchanged"] is True,
        "original_pair_summary_changed")
    native = {}
    for engine, status in [("icarus", "PASS"), ("verilator", "FAILURE_GUARD")]:
        value = row[engine]
        expected = {"compile", "run", "oracle"} | ({"build"} if engine == "verilator" else set())
        require(
            value["status"] == status and value["runtime_executed"] is True
            and value["original_oracle_accepted"] is (engine == "icarus")
            and value["private_fixture_input_mutations"] == []
            and set(value["stages"]) == expected, "original_engine_contract_changed")
        compile_args = value["stages"]["compile"]["invoked_argv"]
        tool = "iverilog" if engine == "icarus" else "verilator_driver"
        require(compile_args[0] == binding["tools"][tool]["path"],
                "original_compile_program_changed")
        expected_compile = (["-o", "work/a.out", *FLAGS, PARSER_FIELDS["source"]]
                            if engine == "icarus" else [
                                "--cc", "--exe", "--main", "--assert", "--timing", "--fourstate",
                                "--no-skip-identical", "-Wno-fatal", "--Mdir", "obj", "--prefix",
                                "Vt", "--default-language", "1364-2005", "--default-language",
                                "1800-2005", "-D__ICARUS_UNSIZED__", PARSER_FIELDS["source"]
                            ])
        require(compile_args[1:] == expected_compile, "original_compile_options_changed")
        native[engine] = {}
        for name, record in value["stages"].items():
            result = fixed.stage_record(pair, recorded, index, engine, name, record, False, 128)
            code = 1 if engine == "verilator" and name == "oracle" else 0
            require(
                result["actual_exit"] == code and result["raw_wait_status"] == code * 256
                and result["termination_reason"] is None and record["exited_normally"] is True
                and record["kill_sent"] is False, "original_native_result_changed")
            native[engine][name] = result
        oracle = value["stages"]["oracle"]["invoked_argv"]
        input_path = recorded / f"cases/{index:04d}/{engine}/run.stdout"
        require(
            len(oracle) == 5 and oracle[1:3] == ["-c", ORACLE_PROGRAM]
            and json.loads(oracle[3]) == PARSER_FIELDS and oracle[4] == str(input_path),
            "original_oracle_command_changed")
        output = fixed.bounded(pair, f"cases/{index:04d}/{engine}/run.stdout").read_text()
        expected_lines = [] if engine == "icarus" else ["26", "30", "33", "36"]
        require(
            re.findall(r"^FAILED line (\d+)$", output, re.M) == expected_lines
            and (re.findall(r"^PASSED$", output, re.M) == ["PASSED"]) == (engine == "icarus"),
            "original_failure_output_changed")
    return {
        "schema": "case122-projection-review-v1",
        "head": head,
        "scenario_id": SID,
        "reviewed_classification": "REFERENCE_STANDARD_CONFLICT",
        "original_pair_status": row["pair_status"],
        "original_source_sha256": SOURCE_SHA,
        "original_oracle_sha256": ORACLE_SHA,
        "original_case_result_sha256": sha(fixed.bounded(pair, f"cases/{index:04d}/result.json")),
        "verilator_compiler_sha256": compiler_sha,
        "raw_pair_status_counts": counts,
        "raw_output_difference_count": counts["UNREVIEWED_OUTPUT_DIFFERENCE"],
        "reviewed_case_count": 1,
        "standard": standard(root, head, standard_root, regression_root),
        "native_evidence": native,
        "semantic_gate_unchanged": True,
        "overall_acceptance": False,
        "review_gate_exit": 0
    }


def core_fields(data):
    """Relay only typed case122 metadata, without replacing any original gate."""
    require(
        data["scenario_id"] == SID
        and data["reviewed_classification"] == "REFERENCE_STANDARD_CONFLICT"
        and data["original_pair_status"] == "UNREVIEWED_OUTPUT_DIFFERENCE"
        and data["original_source_sha256"] == SOURCE_SHA
        and data["original_oracle_sha256"] == ORACLE_SHA
        and data["semantic_gate_unchanged"] is True and data["overall_acceptance"] is False
        and type(data["review_gate_exit"]) is int and data["review_gate_exit"] == 0,
        "typed_case122_review_invalid")
    require(
        type(data["reviewed_case_count"]) is int and data["reviewed_case_count"] == 1
        and type(data["raw_output_difference_count"]) is int
        and data["raw_output_difference_count"] >= 1, "typed_case122_count_invalid")
    require(re.fullmatch(r"[0-9a-f]{40}", data["head"]), "typed_case122_head_invalid")
    require(re.fullmatch(r"[0-9a-f]{64}", data["verilator_compiler_sha256"]),
            "typed_case122_compiler_invalid")
    std = data["standard"]
    require(
        std["status"] == "PASS" and type(std["checks_per_profile"]) is int
        and std["checks_per_profile"] == 100 and std["profiles"] == ["two", "four"]
        and std["raw_wait_status"] == "NOT_RECORDED"
        and std["scope"] == "harness_checked_return_and_assertions"
        and len(std["logs_sha256"]) == 2 and all(
            re.fullmatch(r"[0-9a-f]{64}", x)
            for x in [std["source_sha256"], std["driver_sha256"], *std["logs_sha256"]]),
        "typed_standard_review_invalid")
    keys = ("head", "scenario_id", "reviewed_classification", "original_pair_status",
            "original_source_sha256", "original_oracle_sha256", "semantic_gate_unchanged",
            "overall_acceptance", "review_gate_exit", "raw_output_difference_count",
            "reviewed_case_count", "verilator_compiler_sha256")
    return {
        **{
            key: data[key]
            for key in keys
        }, "standard": {
            key: std[key]
            for key in ("status", "checks_per_profile", "profiles", "raw_wait_status", "scope",
                        "source_sha256", "driver_sha256", "logs_sha256")
        }
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("root", "pair", "source", "inventory", "select", "output"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--expected-head", required=True)
    parser.add_argument("--standard-root", type=Path)
    parser.add_argument("--regression-root", type=Path)
    args = parser.parse_args()
    try:
        result = collect(args.root, args.pair, args.source, args.inventory, args.select,
                         args.expected_head, args.standard_root, args.regression_root)
    except (OSError, ValueError, KeyError, IndexError, TypeError,
            subprocess.CalledProcessError) as error:
        result = {
            "schema": "case122-projection-review-v1",
            "head": args.expected_head,
            "scenario_id": SID,
            "reviewed_classification": "NOT_APPLIED",
            "review_gate_exit": 2,
            "semantic_gate_unchanged": True,
            "overall_acceptance": False,
            "reason": type(error).__name__ + ": " + str(error)
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print("CASE122_PROJECTION_REVIEW " + json.dumps(result, sort_keys=True))
    return result["review_gate_exit"]


if __name__ == "__main__":
    raise SystemExit(main())
