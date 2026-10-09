#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run explicit cloud regression groups and record their actual test counts."""

import json
import re
import subprocess
import sys
from pathlib import Path

GROUPS = {
    "amd-repair": [
        "fourstate_blocking_delay", "fourstate_cond_scale", "fourstate_drive_buffer",
        "fourstate_drive_deassign", "fourstate_drive_unsup", "fourstate_implicit_delay",
        "fourstate_monitor_postponed", "fourstate_negate", "fourstate_negate_mask",
        "fourstate_packed_index", "fourstate_slice_bounds", "fourstate_zero_domain",
        "select_signed_domain", "timing_implicit_delay", "timing_monitor_postponed",
        "timing_zero_domain"
    ],
    "deassign": ["assign_deassign_clocked", "fourstate_deassign_clocked"],
    "capabilities":
    ["fourstate_mac_model", "fourstate_mem_index", "fourstate_shiftrs", "fourstate_supplies"],
    "followup": [
        "fourstate_case", "fourstate_case_const", "fourstate_case_inside", "fourstate_case_onehot",
        "fourstate_delay", "fourstate_delay_int", "fourstate_demo_json", "fourstate_iface_array",
        "fourstate_inst", "fourstate_membersel_sideeffect", "fourstate_pull_default",
        "fourstate_queue2", "fourstate_real_conv", "fourstate_saif_time", "fourstate_trace_saif"
    ],
    "extended": [
        "fourstate_arithmetics", "fourstate_assign_complex", "fourstate_assign_sel_lhs",
        "fourstate_comparison", "fourstate_complex_pin", "fourstate_concat", "fourstate_countbits",
        "fourstate_eqwild", "fourstate_event_detection", "fourstate_extend", "fourstate_logand",
        "fourstate_logor", "fourstate_neqwild", "fourstate_redand", "fourstate_redor",
        "fourstate_redxor", "fourstate_replicate", "fourstate_sel", "fourstate_shift"
    ],
    "integration": ["fourstate_coverage"],
    "finish_slice": ["finish_final_local", "finish_process_exit"],
    "fourstate": [
        "fourstate_api", "fourstate_cond", "fourstate_countones", "fourstate_dynarray",
        "fourstate_format", "fourstate_format_bin", "fourstate_format_hex",
        "fourstate_format_octal", "fourstate_isunknown", "fourstate_lognot", "fourstate_modport",
        "fourstate_noapi", "fourstate_packed_array", "fourstate_portable",
        "fourstate_sampled_expr", "fourstate_struct", "fourstate_trace_fst", "fourstate_trace_vcd",
        "fourstate_vpi", "vpi_get", "vpi_get_value_array"
    ],
    "nba": [
        "assigndly_deep_ref_array", "assigndly_dynamic", "assigndly_dynamic_delay",
        "disable_fork_nba", "fork_jumpblock", "fourstate_event_vector", "fourstate_nba_loop",
        "nba_commit_queue", "nba_commit_queue_suspenable", "nba_mixed_update_clocked",
        "nba_mixed_update_comb", "nba_partial_late", "select_bound_timing_intra",
        "struct_array_assignment_delayed", "timing_event_time", "timing_fork_join",
        "timing_intra_assign", "timing_intra_assign_nolocalize", "timing_nba_1", "timing_nba_2",
        "timing_nba_loop", "timing_wait_fork_split", "unroll_delay"
    ],
    "pull": ["fourstate_pull_release", "fourstate_pull_release_unsup"],
    "readmem": [
        "fourstate_readmem", "fourstate_readmem_bad", "fourstate_readmem_range",
        "fourstate_readmem_unsup", "sys_readmem", "sys_readmem_4state", "sys_readmem_assoc",
        "sys_readmem_assoc_bad", "sys_readmem_bad_addr", "sys_readmem_bad_addr2",
        "sys_readmem_bad_digit", "sys_readmem_bad_end", "sys_readmem_bad_notfound",
        "sys_readmem_eof", "sys_writemem", "sys_writemem_b"
    ],
    "resolve": [
        "fourstate_resolve_pair", "fourstate_resolve_triple", "fourstate_resolve_events",
        "fourstate_resolve_unsup", "fourstate_resolve_defaults"
    ],
    "upstream": [
        "class_param_enum", "class_static_default_arg", "class_type_param_upcast_chain",
        "debug_emitv", "fork_join_none_any_nested", "fork_join_none_nested_triggered",
        "inst_array_partial", "inst_sv", "math_shift", "math_shift_extend", "math_shiftls",
        "math_shiftrs", "mem", "mem_fifo", "mem_multi_io", "param_array", "param_shift",
        "param_type", "paramgraph_iface_template_mismatch", "process_kill", "sampled_sensitivity",
        "struct_pat", "struct_unpacked_clean", "struct_unpacked_init_param", "timing_always",
        "timing_intra_assign_func"
    ]
}


def parse_summary(log_text):
    """Read the sole completed harness summary, including any retry failures."""
    summaries = re.findall(r"^==TESTS DONE, ([^\n]*)$", log_text, re.MULTILINE)
    if len(summaries) != 1:
        raise ValueError("Expected exactly one completed harness summary")
    status, separator, summary = summaries[0].partition(": ")
    if not separator or status not in ("PASSED", "FAILED", "PASSED w/SKIPS"):
        raise ValueError("Unrecognized harness summary")
    pairs = re.findall(r"\b(Passed|Failed(?:-First)?|Skipped|Left|Running) (\d+)\b", summary)
    counts = {key.lower(): int(value) for key, value in pairs}
    if len(counts) != len(pairs) or not {"passed", "failed"}.issubset(counts):
        raise ValueError("Missing or duplicate harness counts")
    return status, counts


def passed_counts(status, counts, expected):
    """Accept only a completed selection with no failures or skipped tests."""
    return (status == "PASSED" and counts.get("passed") == expected and counts.get("failed") == 0
            and all(
                counts.get(key, 0) == 0 for key in ("failed-first", "skipped", "left", "running")))


def passed_names(log_text, selected):
    """Require one actual harness pass record for each selected driver."""
    actual = re.findall(r"^vlt/(t_[A-Za-z0-9_]+): Self PASSED$", log_text, re.MULTILINE)
    expected = {"t_" + name for name in selected}
    return len(actual) == len(selected) == len(set(actual)) and set(actual) == expected


# Keep per-group execution, exit status, and result recording together for auditing.
def run_groups(root, groups):  # pylint: disable=too-many-locals
    """Record every selected group even when an earlier subprocess fails."""
    if not groups or len(set(groups)) != len(groups) or any(group not in GROUPS
                                                            for group in groups):
        raise ValueError("Select distinct, known regression groups")
    selected = [name for group in groups for name in GROUPS[group]]
    if len(selected) != len(set(selected)):
        raise ValueError("Regression groups select duplicate test names")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    for directory in ("logs", "out"):
        (root / directory).mkdir(exist_ok=True)
    results = {}
    failed = False
    for group in groups:
        names = GROUPS[group]
        drivers = ["t/t_" + name + ".py" for name in names]
        for driver in drivers:
            if not (root / "test_regress" / driver).is_file():
                raise FileNotFoundError(driver)
        command = [sys.executable, "driver.py", "--vlt", "-j2", "--no-skip-identical", *drivers]
        with (root / "logs" / (group + "-regressions.log")).open("w") as log, subprocess.Popen(
                command,
                cwd=root / "test_regress",
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True) as process:
            for line in process.stdout:
                log.write(line)
                print(line, end="", flush=True)
            returncode = process.wait()
        log_text = (root / "logs" / (group + "-regressions.log")).read_text()
        status = "INVALID"
        counts = {}
        try:
            status, counts = parse_summary(log_text)
        except ValueError as error:
            print(group + ": " + str(error), file=sys.stderr)
        passed = (returncode == 0 and passed_counts(status, counts, len(names))
                  and passed_names(log_text, names))
        results[group] = {
            "commit": head,
            "selected": names,
            "expected": len(names),
            "returncode": returncode,
            "counts": counts,
            "summary_status": status,
            "success": passed
        }
        failed = failed or not passed
    (root / "out" / "regression-results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 1 if failed else 0


def main():
    """Run the named regression groups in this checkout."""
    root = Path(__file__).resolve().parents[2]
    try:
        return run_groups(root, sys.argv[1:])
    except ValueError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    sys.exit(main())
