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
    "finish_slice": [
        "finish_final_local", "finish_process_exit", "fourstate_finish_final",
        "fourstate_finish_process"
    ],
    "finish_propagation": ["finish_final_multi", "finish_call_propagation"],
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
    "plusargs": [
        "fourstate_plusargs", "fourstate_plusargs_unsup", "sys_plusargs", "fourstate_sys_plusargs",
        "fourstate_plusargs_format"
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
    ],
    # Official changes through c265bd444cd9307fad42f03b45068d7662c3adfc.
    "upstream_sync_20261010": [
        "case_cond_item", "clocking_ddr", "clocking_timing_off", "cover_sequence_sampled",
        "covergroup_iff", "fourstate_case_cond", "lint_multidriven_clocking_bad", "math_countbits",
        "mem_bound_bad", "opt_split_no", "packed_array_index_wide_signed", "param_cond_pattern",
        "param_cond_pattern_bad", "param_cond_pattern_unsup", "select_bad_range", "vpi_multidim"
    ],
    # Official changes through 87f76381f71c411811942d29ed4fb5877b623b5b.
    "upstream_sync_20261011": [
        "always_reorder_class", "opt_decompose_packed", "opt_decompose_unpacked",
        "opt_decompose_packed_attr_bad", "opt_decompose_unpacked_attr_bad", "sys_readmem_descend",
        "vpi_packed_struct", "vpi_struct_members_many"
    ],
    "icarus_semantics":
    ["fourstate_nba_event_concat", "fourstate_packed_port_kind", "timing_nba_event_concat"],
    "strict_repairs_20261011": [
        "timing_blocking_event", "fourstate_blocking_event", "fourstate_force_release",
        "force_packed_release"
    ],
    "finish_boundary_20261011": ["timing_finish_boundary", "fourstate_finish_boundary"],
    # Official changes through b7515159bb194d0da6077ff180ef312039aadcdf.
    "upstream_daily_20261012": [
        "assign_automatic_bad", "ast_dump_patterns", "clocking_drive_cycle", "dfg_peephole",
        "disable_task_arg", "event_nba_timing", "flag_deprecated_bad", "nba_struct_array",
        "opt_bitblast", "opt_bitblast_attr", "opt_bitblast_attr_bad", "opt_bitblast_off",
        "param_name_unresolved", "param_name_unresolved_bad", "queue_bounded", "timing_debug1",
        "timing_osc"
    ],
    "sv_controls_20261012": [
        "fourstate_array_guard", "fourstate_array_init", "fourstate_nba_capture",
        "fourstate_nba_race", "fourstate_nba_tasks", "fourstate_nba_trigger",
        "fourstate_nba_unknown", "fourstate_port_api", "fourstate_port_init",
        "fourstate_port_partial", "fourstate_port_static", "fourstate_trace_resume"
    ],
    # Official changes through b8e7f1e4b508f7827894784145cf52cffc3d08d5.
    "upstream_daily_20261013": [
        "covergroup_args_expr_bad", "covergroup_cross_opt_unsup", "covergroup_cross_ref_bad",
        "covergroup_cross_with", "covergroup_cross_with_limits", "covergroup_unsup",
        "covergroup_unsup_ign2", "covergroup_with_type_bad", "covergroup_with_unsup", "enum_type",
        "enum_type_bad", "flag_top_module_encode", "string_type_methods"
    ],
    # Official changes through cf89d898e2e6a047231a886d41179d099ff9a46f.
    "upstream_daily_20261014": [
        "clocking_output_iface", "clocking_output_unsup", "covergroup_incdec", "math_signed3",
        "property_nested_instance", "property_nested_instance_bad",
        "property_nested_instance_cover", "property_nested_instance_unsup",
        "property_recursive_unsup"
    ],
    # Official changes through 75b107a6e94265102850fca288ff493948051f20.
    "upstream_daily_20261014_followup": ["clocking_event_or"],
    # Official changes through af1b121e3f0af489e7129265bfbb3f48800cf2cd.
    "upstream_daily_20261015": [
        "case_extend", "clocking_zero_delay", "cond_logic_and_complex_types", "coverage_prop_seq",
        "enum_value_assign", "event_control_expr", "expr_types", "flag_csplit", "inc_relink",
        "json_only_flat", "opt_cond_double", "randomize_param_target_bad",
        "sequence_arg_delay_bad", "sequence_ref", "sys_sscanf", "x_assign_unique_0",
        "x_assign_unique_1"
    ],
    "finish_coverage_20261015": ["finish_coverage"],
    # Official changes through 1d0bf5d1d1766ed98693cfa95dce2c0ae4659ef4.
    "upstream_sync_20261017": [
        "math_pow3", "lint_widthdigits", "lint_widthdigits_bad", "param_array_2d",
        "param_array_order", "param_array8", "param_struct_unpacked", "param_struct_unpacked_bad",
        "func_const_struct", "func_const_struct_bad", "assignment_array_size_bad",
        "assignment_compatibility_bad", "fourstate_assign_bad", "clocking_drive_same",
        "clocking_skew_round", "clocking_skew_sampled", "vpi_interface_ref",
        "vpi_interface_ref_array", "vpi_interface_ref_lifecycle", "vpi_scope_topology",
        "interface_virtual_modport_bad", "assert_disable_iff_async", "prop_always", "uniqueif",
        "opt_const_static_dead", "display_m_combine", "scope_shared",
        "flag_output_groups_max_size", "flag_output_groups_max_size_bad", "class_extends_this",
        "randcase", "covergroup_with_sample_warn", "covergroup_sized_bad"
    ],
    "sv_semantics_20261026": [
        "flag_language_noconfig", "flag_language_noconfig_bad", "fourstate_inout_default",
        "fourstate_nba_partselect_clip", "fourstate_nba_repeat_control", "fourstate_reduce_scalar",
        "fourstate_sen_expr", "fourstate_sen_iff", "fourstate_case_equal_known", "fourstate_sen_impure_unsup",
        "fourstate_wildcard", "fourstate_nba_clip_bounds", "timing_nba_clip_bounds",
        "timing_nba_partselect_clip", "timing_nba_repeat_control", "timing_nba_repeat_unsup",
        "tri_inout_default"
    ],
    "fourstate_constructors_20261026": [
        "fourstate_cons_copy", "fourstate_cons_keyed", "fourstate_cons_queue",
        "fourstate_cons_struct", "fourstate_cons_unpacked_unsup"
    ],
    # New official constructor, scheduling, VPI and side-effect regressions through cecfb438.
    "upstream_sync_20261026": [
        "dynarray_new_pattern",
        "dynarray_concat",
        "dynarray_unpacked",
        "array_pattern_concat",
        "unpacked_concat",
        "unpacked_concat_noslice",
        "queue_concat_type_param",
        "assoc",
        "assoc_wildcard",
        "const_pool",
        "vpi_param",
        "nba_noninlined_await",
        "opt_inline_getters",
        "opt_inline_getters_off",
        "expr_shortcircuit",
        "case_impure",
        "const_zero_impure",
        "dynarray_unpacked_size_bad",
        "pattern_key_bad",
        "pattern_key_unsup",
    ],
    "tri_storage_20261026": [
        "tri_proc_reassign", "tri_proc_reassign_timing", "tri_various", "tri_inout", "tri_inz",
        "tri_struct", "tri_top_en_out", "tri_pullvec"
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
