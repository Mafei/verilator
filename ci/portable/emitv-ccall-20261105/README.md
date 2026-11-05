<!-- SPDX-FileCopyrightText: 2026 Mafei -->
<!-- SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

# CCall diagnostic argument boundaries

PR54 at `65440def6998f1258c3ef52cb4a698ddd43b96a5` remains the frozen
baseline. Its [CI41946187799](https://github.com/Mafei/verilator/actions/runs/41946187799)
reported 557 passed and five failed selected drivers on each platform.
The full audit failed with `ast_original_golden_mismatch`. Original
fixtures, expected files, reference comparisons and failed gates stay intact.

## Proven defect and narrow correction

A minimal public DPI input produces three separate `AstCCall::argsp`
children for `left`, `right` and a return temporary. The baseline task-stage
Verilog diagnostic concatenates them, for example
`__Vdpiimwrap_t__DOT__dpi_pair_TOP(leftright t.__VlemCall_0__dpi_pair)`.
Reversing the source arguments prints `rightleft`. The generated C++
correctly keeps the three arguments separate. This proves diagnostic
information loss, not a simulation-semantics defect.

The CCall visitor now uses the existing comma-separated visitor. V3Task
prepends a ScopeName node to context-DPI arguments; the Verilog visitor
intentionally emits no text for that node. Skipping this first hidden node
before emitting separators preserves the existing scope policy and avoids
an empty leading argument. Other ScopeName visitors are unchanged.

Synthetic C++ `argTypes` text remains outside this narrow correction.
Post-task diagnostics also contain CFUNC placeholders and C-expression
wrappers, and are not a complete round-trip SystemVerilog or C++ ABI
representation. The tests must not imply otherwise. Known-valued runtime
DPI controls do not establish X/Z argument transport support.

The independent driver checks normal and reversed pairs, context calls with
filename and line metadata, one argument, and a genuinely empty task argument
list in both two-state and four-state modes. It then runs 32 bounded signed
DPI iterations per mode, with 258 assertions in each model. The generated
main explicitly names its instance TOP, so the strict declaration-scope check
uses TOP.t even when the call is in a named inner block. The imported DPI task
helper returns the required integer completion status. No runtime assertion
is weakened to accommodate fixture configuration mistakes.

## Original failures remain failed

| Driver | Preserved evidence and unresolved boundary |
| --- | --- |
| debug_emitv | Frozen widthcommit golden begins with `module Vt_debug_emitv_t`; current output begins with `module t`. Widthcommit precedes creation of these CCalls, so this change cannot repair that mismatch or its AST audit. |
| fourstate_pull_unsup | Current diagnostic rejects a nonlocal multiple-driver net; old expected text rejects pullups/pulldowns. A controlled unsupported diagnostic is not a model pass or implemented nonlocal resolution. |
| opt_merge_cond_no_motion | The model completes its checks, but the exact optimization-count oracle still rejects 649 versus 585. This change does not alter either count or the oracle. |
| timing_debug2 | Strict trace comparison still differs in class-name escaping and post-finish dispatch text. Existing raw trace and expected text remain unchanged. |
| assert_ctl_arg | Exact official expected text retains six concurrent assertion lines after All Finished, while the baseline model stops at its finish request. The later coverage-file comparison is not reached. Its original failure and acceptance classification are retained. |

The old five-driver failure reduction from this patch is zero. Its
maintained regression checks a separate, demonstrated debug-output defect.
No expected file or comparator is relaxed to make either set pass.

Draft/HOLD. No release or delivery-branch promotion. Final-source evidence
belongs to the candidate's own commit and CI, never to transferred PR54
counts.
