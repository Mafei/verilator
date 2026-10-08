#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run explicit cloud regression groups and record their actual test counts."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys


GROUPS = {
    "capabilities": """
        fourstate_mac_model fourstate_mem_index fourstate_shiftrs
        fourstate_supplies
    """.split(),
    "extended": """
        fourstate_arithmetics fourstate_assign_complex fourstate_assign_sel_lhs
        fourstate_comparison fourstate_complex_pin fourstate_concat
        fourstate_countbits fourstate_eqwild fourstate_event_detection
        fourstate_extend fourstate_logand fourstate_logor fourstate_neqwild
        fourstate_redand fourstate_redor fourstate_redxor fourstate_replicate
        fourstate_sel fourstate_shift
    """.split(),
    "integration": ["fourstate_coverage"],
    "fourstate": """
        fourstate_api fourstate_cond fourstate_countones fourstate_dynarray
        fourstate_format fourstate_format_bin fourstate_format_hex
        fourstate_format_octal fourstate_isunknown fourstate_lognot
        fourstate_modport fourstate_noapi fourstate_packed_array
        fourstate_portable fourstate_sampled_expr fourstate_struct
        fourstate_trace_fst fourstate_trace_vcd fourstate_vpi vpi_get
        vpi_get_value_array
    """.split(),
    "upstream": """
        class_param_enum class_static_default_arg class_type_param_upcast_chain
        debug_emitv fork_join_none_any_nested fork_join_none_nested_triggered
        inst_array_partial inst_sv math_shift math_shift_extend math_shiftls
        math_shiftrs mem mem_fifo mem_multi_io param_array param_shift param_type
        paramgraph_iface_template_mismatch process_kill sampled_sensitivity
        struct_pat struct_unpacked_clean struct_unpacked_init_param
        timing_always timing_intra_assign_func
    """.split(),
}


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise SystemExit("Run regressions in GitHub Actions")
    root = Path(__file__).resolve().parents[2]
    results = {}
    failed = False
    for group in sys.argv[1:]:
        names = GROUPS[group]
        drivers = ["t/t_" + name + ".py" for name in names]
        for driver in drivers:
            if not (root / "test_regress" / driver).is_file():
                raise FileNotFoundError(driver)
        command = [sys.executable, "driver.py", "--vlt", "-j2", *drivers]
        with (root / "logs" / (group + "-regressions.log")).open("w") as log:
            process = subprocess.Popen(command, cwd=root / "test_regress",
                                       stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                log.write(line)
                print(line, end="", flush=True)
            returncode = process.wait()
        text = (root / "logs" / (group + "-regressions.log")).read_text()
        summary = re.findall(r"==TESTS DONE,.*", text)
        counts = {}
        if summary:
            counts = {key.lower(): int(value) for key, value in
                      re.findall(r"(Passed|Failed|Skipped) (\d+)", summary[-1])}
        passed = (returncode == 0 and counts.get("passed") == len(names)
                  and counts.get("failed") == 0 and counts.get("skipped", 0) == 0)
        results[group] = {"selected": names, "expected": len(names),
                          "returncode": returncode, "counts": counts,
                          "success": passed}
        failed = failed or not passed
    (root / "out" / "regression-results.json").write_text(
        json.dumps(results, indent=2) + "\n")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
