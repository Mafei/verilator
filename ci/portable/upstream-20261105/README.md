<!-- SPDX-FileCopyrightText: 2026 Mafei -->
<!-- SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

# November 5 upstream candidate

This candidate normally merges official
`57bbb293d2d41274233674be0d866183de4fa224` into PR53
`22832cb42fe81503749ac43de00fe674d297dbaa`, retaining both parents and all
eight new official commits. Both Antmicro heads remain contained:
`dbb8aedaa478389639295e40f16dbc7183d10b48` and
`5e132f32db577b3d596b66ce6378ac224ffa38d3`.

The conflict resolution retains the fork's selected-Z rewrite restriction
together with the new `constRemoveXs()` guard, keeps `opBitsOneX`, adopts
the upstream X/Z operations, and retains the fork's monitor-request path
alongside the new observed-deferred assertion helpers. The obsolete
monitor-pending helper is not restored.

`upstream-gold-20261105.json` records all 19 affected expected-output files.
Eighteen adopt exact official bytes because the previous fork and official
versions were identical. The diverged debug AST golden stays frozen. No
observed local output generates a replacement for an existing golden.
Upstream automation changes remain in `ci/upstream-workflows`, retaining
the fork's inactive-workflow policy.

## Reactive finish regression

The unpatched merge lets an observed assertion task execute a statement
after `$finish`. The same input's finish checks pass on the PR53 compiler.
The two source-process eligibility decisions in `V3Finish` now use one
shared predicate that also recognizes `AlwaysReactive`. Final, fork,
expression, DPI/public and shared-task restrictions remain unchanged.

The two new runtime drivers each exercise inline and no-inline tasks,
with two-state and four-state profiles. They require an actual finish
diagnostic, reject a later statement within the finishing task, and check
final execution. Another queued action may run before finish; the checks
do not require an arbitrary ordering between those actions. Their output
is rejected if it follows the actual finish diagnostic in this
single-threaded model.

Before the fix, both drivers fail their inline case with real harness
exit 10/raw wait status 2560. With the fix, both drivers complete all four
model runs, exit/raw 0/0. This checks the observed finish behavior; it does
not establish complete deferred-assertion or SystemVerilog compliance.

Thirty upstream-related drivers and these two fork integration drivers
are appended to the unchanged ordered 530-driver prefix, giving 562
drivers in 48 groups. The original 438 projection, original failures,
Strict18/fixed128 inputs and pending classification decisions remain.

## Remaining boundaries

The public `probes/observed_xz_arguments_unsupported.sv` input is still
rejected at a nested `logic[64:0]$[$]` four-state queue type. No model runs
or X/Z argument checks occur for that input. It is retained as an
unsupported probe, outside runtime pass totals. The initial no-inline
probe with external module-variable references also reaches the existing
IMPURE boundary; the maintained finish test uses tasks without those
external references to isolate the finish defect.

Old AST/output golden conflicts and failed gates remain visible. Native
checks do not substitute for final-source macOS ARM64 and Rocky8.10
build, relocation, reference and semantic acceptance. Draft/HOLD; no
release or delivery-branch promotion.
