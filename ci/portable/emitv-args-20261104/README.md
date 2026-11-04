<!-- SPDX-FileCopyrightText: 2026 Mafei -->
<!-- SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

# Function and task argument emission

At parent `728b83c534d7b2d39751d6d7c902d4cc106151fd`, debug Verilog
emission concatenates distinct function/task arguments. For example,
`pair(left, right)` becomes `pair(leftright)`, and named arguments lose the
separator between their wrappers. This defect is also present in calls in
the existing `debug_emitv` fixture.

The parent owns the argument list; each `AstArg` owns only one optional
expression. Use the existing comma-separated traversal at `AstNodeFTaskRef`,
retaining the separate Property path and the individual argument visitor.
This changes debug output, not generated simulation C++ or SV scheduling.

The new `debug_emitv_args` driver has ten text assertions at `cells` and
`widthcommit`. They require commas for positional, named, nested, defaulted,
and explicitly omitted arguments, and retain zero/one-argument controls.
The same final input and driver fail against the saved parent compiler
(harness exit 10, raw wait status 2560) and pass against the patched compiler
(exit/raw 0/0). These are emitted-text checks, not model execution or proof
that the whole debug dump can be parsed back as SystemVerilog.

Only one driver is appended to the existing ordered 529-driver selection.
The previous selection, original 438 projection, goldens, Icarus inputs,
reference results, and pending classification decisions are preserved.

The four original default-regression failures remain visible:

| Test | Evidence and remaining boundary |
| --- | --- |
| `debug_emitv` | The combined fixture and its frozen expected output differ in stage, declarations and expressions. Missing call commas are a confirmed emitter defect; this patch does not approve a complete golden migration. |
| `fourstate_pull_unsup` | The original inout fixture still rejects, now for a multiple-driver nonlocal target rather than four blanket pull-primitive rejections. The legal-but-unsupported boundary remains. |
| `opt_merge_cond_no_motion` | Actual counters are 11/649/127 versus 11/585/64. The extra 64 merged items are NBA auxiliary assignments; the observed counter arithmetic is correct. No statistic expectation is changed. |
| `timing_debug2` | Preserve the strict debug-trace comparison. Class-separator spelling and stopping work after finish must be reviewed against their original fixes before any expected-output migration. |

The AST audit uses the same unchanged `debug_emitv` golden and continues to
reject a mismatch. Neither `audit_integrity` nor its exit-2 behavior is
relaxed. No claim is made that these four original failures have passed.

Internal `AstCCall` argument rendering also needs investigation: it can
contain metadata whose current visitor emits no text, so blindly applying
this traversal there would produce an empty leading argument. That path,
the missing SystemC-section debug coverage, and a full golden migration are
outside this one-line fix. Draft/HOLD remains until the existing acceptance
and evidence gates are satisfied.
