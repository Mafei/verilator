#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run explicit cloud regression groups and record their actual test counts."""

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from compile_cache import reclaim_completed

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
    "finish_propagation": [
        "finish_final_multi", "finish_call_propagation", "finish_coverage_tails",
        "finish_coverage_barrier", "while_finish", "fork_cfunc_finish"
    ],
    "fourstate": [
        "fourstate_api", "fourstate_cond", "fourstate_countones", "fourstate_dynarray",
        "fourstate_format", "fourstate_format_bin", "fourstate_format_hex",
        "fourstate_format_octal", "fourstate_format_packed", "fourstate_format_real",
        "fourstate_format_trunc", "fourstate_isunknown", "fourstate_lognot", "fourstate_modport",
        "fourstate_noapi", "fourstate_packed_array", "fourstate_portable",
        "fourstate_purity_cache", "fourstate_sampled_expr", "fourstate_struct",
        "fourstate_trace_fst", "fourstate_trace_vcd", "fourstate_vpi", "vpi_get",
        "vpi_get_value_array", "port_repeat_output", "port_repeat_scalar",
        "port_repeat_actual_unsup", "port_repeat_complex_unsup", "port_repeat_driver_unsup",
        "port_repeat_inout_unsup", "port_repeat_input_unsup", "port_repeat_mode_unsup",
        "port_repeat_named_unsup", "port_repeat_same_unsup", "port_repeat_top_unsup",
        "var_dup_bad", "lint_pindup_bad", "sched_susp_vs_nosusp", "fourstate_sense_init"
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
        "covergroup_incdec", "math_signed3", "property_nested_instance",
        "property_nested_instance_bad", "property_nested_instance_cover",
        "property_nested_instance_unsup", "property_recursive_unsup"
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
        "flag_language_noconfig", "flag_language_noconfig_bad", "fourstate_gate_init",
        "fourstate_inout_default", "fourstate_lambda_int", "fourstate_nba_partselect_clip",
        "fourstate_nba_repeat_control", "fourstate_queue_projection", "fourstate_reduce_scalar",
        "fourstate_sen_expr", "fourstate_sen_iff", "fourstate_case_equal_known",
        "fourstate_sen_impure_unsup", "fourstate_wildcard", "fourstate_nba_clip_bounds",
        "timing_nba_clip_bounds", "timing_nba_partselect_clip", "timing_nba_repeat_control",
        "timing_nba_repeat_unsup", "tri_inout_default", "func_ancestor_ctx",
        "func_ancestor_func_unsup", "func_ancestor_import_unsup", "func_ancestor_missing_bad",
        "func_ancestor_param_unsup", "func_ancestor_suggest_bad", "func_ancestor_wrongkind_unsup",
        "func_ancestor_xz", "import_context_capture", "package_import_lexical", "queue_slice",
        "net_dtype_bad", "net_dtype_packed", "net_dtype_unpacked_bad", "type_compare"
    ],
    "fourstate_constructors_20261026": [
        "fourstate_cons_copy", "fourstate_cons_keyed", "fourstate_cons_queue",
        "fourstate_cons_struct", "fourstate_cons_unpacked_unsup"
    ],
    # New official constructor, scheduling, VPI and side-effect regressions through cecfb438.
    "upstream_sync_20261026": [
        "stream_unpack_wider",
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
    ],
    "optimizer_alias_20261026": [
        "opt_merge_cond", "opt_merge_cond_member", "opt_subst", "opt_subst_off",
        "func_out_short_circuit", "func_arg_purity"
    ],
    # Official fixes throughbe33a0f6; sampler positives need an available solver.
    "upstream_late_20261026": [
        "fork_taskarg", "timing_sched_ready", "sys_monitor_changes", "opt_reloop_inlined",
        "opt_expand_keep_widths", "constraint_rand_sampler_bad", "constraint_rand_sampler_env_bad",
        "restorer_clear"
    ],
    "sv_read_string_20261026": [
        "fourstate_slice_index_domain", "fourstate_slice_index_width",
        "fourstate_slice_index_width_bad", "fourstate_slice_packed_domain", "string_byte",
        "string_unpacked_literal", "fourstate_struct_select", "fourstate_nested_select"
    ],
    # Official changes through ad839901aebcaecd639f9d71443fc5bf13347638.
    "upstream_daily_20261029": [
        "class_param_bits_const", "dpi_argtype_bad", "dpi_open_dyn", "dpi_open_dyn_unsup",
        "dpi_open_packed", "dpi_open_packed_bad", "dpi_open_query", "dpi_struct_unpacked_unsup",
        "dpi_unpack_bad", "fourstate_dpi_open_unsup", "iface_typedef_param_bits",
        "queue_empty_bad", "wire_net_test"
    ],
    # Official changes through 453b02a33cf3a569a57f853aad3fc5d1523517ab.
    "upstream_daily_20261030":
    ["trace_dumpvars_sparse_fst", "trace_dumpvars_sparse_saif", "trace_dumpvars_sparse_vcd"],
    # Official changes through 92ac4051b66ab409351361910b865b9db98b816e.
    "upstream_daily_20261031": [
        "class_scope_nonvirtual", "class_static_method", "cuse_iface",
        "randomize_method_with_scoping", "unroll_stmt", "trace_dumpvars_dyn_0_cc_fst",
        "trace_dumpvars_dyn_0_cc_saif", "trace_dumpvars_dyn_0_cc_vcd",
        "trace_dumpvars_dyn_1_cc_fst", "trace_dumpvars_dyn_1_cc_saif",
        "trace_dumpvars_dyn_1_cc_vcd"
    ],
    # The two original clocking drivers are replayed and audited separately;
    # this revision removes two stale contracts and adds two distinct drivers.
    "clocking_contract_20261031": ["clocking_port_connections", "fourstate_clocking_out_unsup"],
    "output_lvalue_20261031": ["inst_output_lvalue", "inst_output_value_bad"],
    # Official enum conditional typing plus unknown-selector value controls.
    "upstream_daily_20261101": ["enum_cond_type", "fourstate_enum_cond"],
    "upstream_daily_20261102": [
        "assert_unclocked_bad",
        "assign_dynsize_bad",
        "assoc_method_bad",
        "combdly_bad",
        "display_format_wide_decimal",
        "event_nba_automatic_bad",
        "event_nba_dynsize_bad",
        "event_nba_notiming_bad",
        "finaldly_bad",
        "flag_csplit_class",
        "fourstate_pull_unsup",
        "interface_modport_array_ref",
        "lint_multidriven_bad",
        "lint_multidriven_ftask_def_bad",
        "lint_multidriven_proc_bad",
        "pattern_key_size",
        "pull_bitsel",
        "pull_bitsel_whole",
        "randomize_method_with",
        "randomize_param_target",
        "randomize_with_size",
        "sched_noninlined_func_suspendable",
        "sched_noninlined_virt_func_suspendable",
        "sched_noninlined_virt_func_suspendable2",
        "std_randomize_with",
        "string_sel",
        "sys_file_scan3",
        "sys_fscanf_unsup",
        "timing_debug2",
        "to_string_emitted_class_hierarchy1",
        "to_string_emitted_class_hierarchy2",
        "to_string_emitted_class_hierarchy3",
        "to_string_emitted_class_hierarchy4",
        "to_string_emitted_class_hierarchy5",
        "to_string_emitted_class_hierarchy6",
        "tri_pullup_bus",
        "unroll_count_exit",
        "fourstate_wait_eval",
        "timing_wait_eval",
    ],
    "upstream_daily_20261103": [
        "dfg_postponed_active",
        "package_import_wild",
        "package_import_wild_bad",
        "package_import_wild_scale",
        "package_export_unimported_bad",
        "unroll_bit_copy",
        "randomize_solver_reply",
        "constraint_unique_cond",
        "class_name",
        "lint_similarname",
    ],
    "upstream_daily_20261104": [
        "cover_error",
        "flag_j_hier_build",
        "interface_virtual_dispatch",
        "lint_usebeforedecl_bad",
        "opt_combine_dpi",
        "udp_bad_no_output",
        "covergroup_bins_unpack_bad",
        "covergroup_bins_unpack_bad2",
        "covergroup_bins_unpack_bad3",
        "covergroup_bins_unpack_parse_unsup",
        "covergroup_bins_unpack_unsup",
        "enum_type_methods",
        "unpacked_to_queue",
        "struct_cons_cast",
        "opt_merge_cond_no_motion",
        "dpi_open_oob_bad",
        "param_circ_bad",
        "lint_unusedloop_removed_bad",
    ],
    "assoc_ref_20261104": [
        "assoc2",
        "assoc_default_func",
        "assoc_method",
        "assoc_ref_bounds",
        "assoc_ref_type",
        "assocsel_sideeffect",
        "fourstate_assoc_ref_bounds",
        "func_outfirst",
        "oob_2state_array",
        "select_bound1",
        "select_bound2",
        "select_bound3",
        "select_bound_side_effect",
        "select_write_oob_high",
    ],
    "life_ref_20261104": [
        "fourstate_life_ref_alias",
        "func_ref",
        "func_ref_noinline",
        "opt_life",
        "opt_life_off",
        "opt_life_ref_alias",
    ],
    "emitv_args_20261104": ["debug_emitv_args"],
    "upstream_daily_20261105": [
        "assert_cover",
        "assert_cover_off",
        "assert_ctl_arg",
        "assert_obs_defer",
        "assert_obs_defer_bad",
        "assert_obs_defer_default_bad",
        "assert_obs_defer_flush",
        "assert_obs_defer_notiming_bad",
        "assert_obs_defer_ref_bad",
        "assert_obs_defer_unsup",
        "assert_obs_finish",
        "const_bad",
        "covergroup_coverpoint_method_unsup",
        "covergroup_coverpoint_weight",
        "covergroup_coverpoint_weight_drop",
        "covergroup_coverpoint_weight_unsup",
        "display",
        "enum_x_bad",
        "fourstate_obs_finish",
        "hier_block_param_lib",
        "implements",
        "interface_virtual_own_type",
        "lint_width_bad",
        "math_repl3_bad",
        "param_complex_unsup",
        "param_type_bad2",
        "param_x_union",
        "param_x_unique",
        "timing_wait_assign",
        "vlcov_covergroup_report",
        "waiveroutput",
        "waiveroutput_multiline",
    ],
    "emitv_ccall_20261105": ["debug_emitv_ccall"],
    "pull_audit_20261105": ["fourstate_multi_unsup"],
    "upstream_daily_20261106_new": [
        "assigndly_dynamic_notiming",
        "class_param_inherit_access_bad",
        "class_param_inherit_access_pin_bad",
        "class_param_inherit_bad",
        "class_param_inherit_pin",
        "class_param_inherit_pin_bad",
        "class_param_inherit_scope",
        "event_nba_notiming",
        "event_nba_struct",
        "force_release_comb_sel",
        "force_release_wide_sel",
        "func_typedef",
        "lint_multidriven_pin_bad",
        "nba_class",
        "nba_closure_combine",
        "nba_func_comb_unsup",
        "nba_generic",
        "nba_generic_func",
        "nba_generic_vif",
        "nba_generic_zerodly",
    ],
    "upstream_daily_20261106_changed": [
        "array_pattern_packed",
        "assignment_pin_bad",
        "cover_toggle",
        "force_immediate_release_port_net",
        "inst_slice",
        "lint_historical",
        "lint_unused",
        "lint_unused_bad",
        "nba_hier",
        "nba_noninlined_await_virtual",
        "nba_shared_flag_reuse",
        "order_blkandnblk_bad",
        "procedure_always_nba",
        "procedure_initial_nba",
        "queue_class",
        "scheduling_virt_iface_class",
        "stream_unpacked_struct_port",
        "unpacked_concat_bad2",
    ],
    "nba_capture_20261106": [
        "nba_event_capture", "fourstate_nba_event_capture", "nba_with_capture",
        "fourstate_nba_with_capture", "assignsel_clip_runtime", "fourstate_nba_clip_padding",
        "fourstate_nba_bounds_sink", "fourstate_nba_static_bounds_sink"
    ],
    "simulate_display_20261106": ["func_display_nonconst_bad", "func_const", "func_const_bad"],
    "upstream_daily_20261107": [
        "class_copy_bad", "class_extern", "class_new_copy_polymorphism",
        "constraint_arr_with_arrsize_unsup", "constraint_json_only", "lint_latch_bad",
        "timing_split_finish", "timing_split_nested"
    ],
    # Official changes through 3c54689240e96dbe5c551232dd3384326a87cbb2.
    "upstream_daily_20261108": [
        "class_implements_param_bad",
        "cover_fsm_compound_reset",
        "cover_genfor",
        "cover_genfor_default",
        "sched_sense_const",
        "unpacked_wide_reverse_copy",
        "unpacked_wide_reverse_copy_noslice",
        "class_implements_inherited",
        "cover_fsm_negative_extract",
        "disable_inside",
        "for_comma",
        "func_check",
        "lint_misindent_bad",
        "lint_width_cast",
        "randsequence",
        "stream_unpack",
    ],
    # Official changes through 73b52215fdb3d598041e73b673d9324bea58b2aa.
    "upstream_daily_20261109": [
        'assert_bang_in_seq', 'assert_consec_rep', 'assert_goto_rep', 'assert_nonconsec_rep',
        'cast_lvalue_bad', 'cast_stream', 'cast_unpacked_struct', 'cast_unpacked_struct_bad',
        'cast_unpacked_struct_fork', 'cast_unpacked_struct_param_bad', 'cast_unpacked_struct_sel',
        'cast_unpacked_struct_unsup', 'class_lparam_struct_field_chain_bad',
        'constraint_array_index', 'constraint_array_index_simple', 'constraint_foreach_classref',
        'constraint_global_nested_randmode', 'constraint_global_randMode',
        'constraint_global_random', 'constraint_mode_ctor', 'constraint_mode_static',
        'constraint_shift_width', 'constraint_solve_before', 'constraint_unpacked_array',
        'constraint_unsat', 'constraint_unsat_nowarn', 'constraint_unsat_protect_ids',
        'cover_fsm_beginif', 'covergroup_auto_bin_max', 'flag_no_unlimited_stack',
        'flag_unlimited_stack', 'fsm_register_wrapper', 'interface_array_loop',
        'interface_virtual_sub_iface', 'json_only_tag', 'modport_export_task', 'past_funcs',
        'property_accept_reject_on', 'property_pkg_temp', 'randc_constraint',
        'randc_enum_constraint', 'randc_wide_constraint', 'randomize_array',
        'randomize_module_var', 'randomize_prepost_nested', 'randomize_rand_mode_static',
        'randomize_randmode_subobj', 'randomize_solve_before_foreach', 'randomize_this_inline',
        'randomize_union', 'sarif', 'sarif_clean', 'sequence_first_match', 'sequence_ref_hier',
        'sequence_sexpr_throughout', 'std_process_self', 'std_randomize_assoc',
        'std_randomize_queue', 'stream_bad', 'stream_unpack_narrower', 'stream_unpacked_struct',
        'tagged_case', 'tagged_if', 'tagged_union', 'timing_func_fork_bad',
        'virtual_interface_member_trigger', 'vpi_comb_protect_ids', 'vpi_comb_trace', 'vpi_force'
    ],
    # Official changes through bb49431e58b6514655b8a58104b809c7f6d256bf.
    "upstream_daily_20261111": [
        'bind_dot_unsup', 'bind_list_unsup', 'class_param_typedef6', 'constraint_assoc_arr_basic',
        'cover_fsm_two_proc_multi', 'defparam', 'defparam_multi', 'defparam_nfound_bad',
        'defparam_nodot', 'emit_memb_limit_force', 'emit_memb_limit_force_protect_ids',
        'emit_memb_limit_nontriv', 'emit_memb_limit_nontriv_disabled',
        'emit_memb_limit_nontriv_large', 'emit_memb_limit_nontriv_single', 'enum_item_ref_scale',
        'event_control_expr_noinl', 'event_control_expr_unsup', 'func_recurse_depth', 'hier_block',
        'hier_block_param_empty', 'if_deep_chain', 'interface_generic_bad4',
        'interface_generic_positional', 'interface_typedef_bad', 'lint_defparam_bad',
        'param_type_cast_deep', 'past', 'preproc', 'preproc_comments', 'preproc_defines',
        'preproc_dump_defines', 'sched_split_debug', 'sched_split_debug_on', 'string',
        'trace_ena_cc', 'wrapper_dup_name_bad'
    ],
}


def selection_revision():
    """Identify both ordered selections, even when their driver counts agree."""
    # Import lazily: the legacy replay imports the harness summary parser here.
    import clocking_legacy  # pylint: disable=import-outside-toplevel

    archive = Path(
        clocking_legacy.__file__).resolve().parent / 'legacy/clocking-8925/manifest.json'
    original = json.loads(archive.read_text())['original_selected_names']

    def digest(names):
        return hashlib.sha256(('\n'.join(names) + '\n').encode()).hexdigest()

    if (len(original) != 438 or len(set(original)) != 438
            or digest(original) != clocking_legacy.ORIGINAL_SELECTOR_SHA256):
        raise ValueError('Original regression selection changed')
    order = [
        *clocking_legacy.ORIGINAL_GROUPS,
        *(name for name in GROUPS if name not in clocking_legacy.ORIGINAL_GROUPS)
    ]
    if len(order) != len(set(order)) or set(order) != set(GROUPS):
        raise ValueError('Missing original regression group')
    current = [name for group in order for name in GROUPS[group]]
    if len(current) != len(set(current)):
        raise ValueError('Duplicate current regression driver')
    removed = [name for name in original if name not in current]
    added = [name for name in current if name not in original]
    unchanged = [name for name in original if name not in removed]
    if (removed != list(clocking_legacy.LEGACY_NAMES)
            or unchanged != [name for name in current if name in original]):
        raise ValueError('Original regression selection delta changed')
    # Preserve the Nov6 merge baseline, including drivers added after the original 438.
    if (len(current) < 564 or digest(current[:564])
            != 'eccc9b91c1c4113668d7e27dd7115478a9d7d9d4962426cf766a8007b9455dba'):
        raise ValueError('Nov6 original regression selection changed')
    if (len(current) < 610 or digest(current[:610])
            != '49cbe37203828ba127798e9d6f6cf1ea43d39da9817f0fa6f2c142b9cf80d459'):
        raise ValueError('Nov6 integrated regression selection changed')
    if (len(current) < 613 or digest(current[:613])
            != '75858628307e413df2ad3ae01c684883a9500a4813fc578eeb4ac7f4e8e50212'):
        raise ValueError('Nov7 inherited regression selection changed')
    if (len(current) < 621 or digest(current[:621])
            != '19971aaf7c550a3744d9c75638bca7f3093aa74f7e2ce7c1f354dbbd0a144fa3'):
        raise ValueError('Nov8 inherited regression selection changed')
    if (len(current) < 637 or digest(current[:637])
            != '96006fd6b3e3679e6c8e43ab6922d78cf4058e5a5a1156bfd5a0304001e74695'):
        raise ValueError('Nov9 inherited regression selection changed')
    if (len(current) < 706 or digest(current[:706])
            != 'b4157e9bd8b268ed44c3b5a8ac740ddf7c8f3db90a69802f2eb181b7d851f000'):
        raise ValueError('Nov11 inherited regression selection changed')
    return {
        'schema': 'clocking-regression-selection-v1',
        'original_revision': clocking_legacy.BASE_SHA,
        'current_revision': 'clocking-contract-20261031',
        'original_selector_sha256': digest(original),
        'current_selector_sha256': digest(current),
        'original_selected_drivers': len(original),
        'current_selected_drivers': len(current),
        'unchanged_drivers': len(unchanged),
        'removed_drivers': removed,
        'added_drivers': added,
    }


def actual_passed_names(log_text):
    """Preserve individual pass identities for the original-selection projection."""
    return re.findall(r"^vlt/t_([A-Za-z0-9_]+): Self PASSED$", log_text, re.MULTILINE)


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
    actual = actual_passed_names(log_text)
    expected = set(selected)
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
    cache_failed = False
    cache_results = {}
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
        # A parent wait alone does not establish that an abnormal harness left no workers.
        # Require its complete, closed summary before touching any compilation cache.
        completed = (returncode >= 0 and status in ('PASSED', 'FAILED')
                     and counts.get('left', 0) == 0 and counts.get('running', 0) == 0
                     and sum(counts.get(key, 0)
                             for key in ('passed', 'failed', 'skipped')) == len(names))
        if not completed:
            cache_results[group] = {
                'schema': 'completed-compile-cache-v1',
                'status': 'incomplete_harness',
                'selected': names,
                'removed': [],
                'bytes': 0,
            }
        else:
            try:
                cache_results[group] = reclaim_completed(root, names)
            except (OSError, ValueError) as error:
                cache_failed = True
                cache_results[group] = getattr(
                    error, 'compile_cache_ledger', {
                        'schema': 'completed-compile-cache-v1',
                        'status': 'infrastructure_failure',
                        'selected': names,
                        'error': str(error),
                    })
                print(group + ': compilation cache reclamation failed: ' + str(error),
                      file=sys.stderr)
        print('COMPILE_CACHE_RECLAIM ' +
              json.dumps({
                  'group': group,
                  'status': cache_results[group]['status'],
                  'bytes': cache_results[group].get('bytes', 0),
                  'removed': len(cache_results[group].get('removed', [])),
              }),
              flush=True)
    (root / 'out/compile-cache-results.json').write_text(
        json.dumps(
            {
                'schema': 'portable-compile-cache-results-v1',
                'commit': head,
                'groups': cache_results,
            },
            indent=2) + '\n')
    (root / "out" / "regression-results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 2 if cache_failed else (1 if failed else 0)


def main():
    """Run the named regression groups in this checkout."""
    root = Path(__file__).resolve().parents[2]
    try:
        return run_groups(root, sys.argv[1:])
    except ValueError as error:
        raise SystemExit(str(error)) from error


if __name__ == "__main__":
    sys.exit(main())
