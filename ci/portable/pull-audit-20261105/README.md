<!-- SPDX-FileCopyrightText: 2026 Mafei -->
<!-- SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

# Preserve explicit pull diagnostic precedence

PR55 at `c157884224dcb7302daafcf5f044e44bada53a80` rejects the original
`t_fourstate_pull_unsup` input at its inout declaration with a generic
multiple-driver/nonlocal-target diagnostic. This prevents the existing
four explicit pull-primitive diagnostics from being reached. Its original
fixture, expected output and failed run remain the baseline.

Defer nets containing an explicit `AstPull` writer to the existing rejection
in `FourstateVisitor`, rather than auditing their deliberately unknown
contributions as generic resolver overlap. Keep early multi-driver membership
protection unchanged. No such net is prepared for resolution, and the existing
error barrier stops compilation after collecting the primitive diagnostics.
The diagnostic text, collection order and unsupported boundary are unchanged.
The first prototype moved rejection earlier, but a mixed-unsupported control
showed that its early abort suppressed six other diagnostics; that prototype
was discarded before committing.

The unchanged regression must match the original golden and the raw log must
contain exactly four unsupported diagnostics at 10:10, 11:10, 12:12 and 13:12,
ending with `Exiting due to 4 error(s)`. Its harness passing means a correct
expected rejection, not a successful simulation of explicit pull primitives.

Implicit `tri0`/`tri1` defaults and their supported whole continuous drivers
are separate constructs. Existing release, resolution, nonlocal-target and
tristate-buffer behavior/guard tests must retain their original assertions and
waveform comparisons. Two-state explicit pull behavior must also remain intact.
Mixed-unsupported fixtures are checked separately as diagnostic controls; they
are not promoted to passing regressions when their old golden still differs.

No old input, expected file, comparator or classification is changed. All
563 previous ordered test identities remain; the existing mixed-unsupported
regression is appended as one additional control, for 564 drivers in 50 groups. The other four selected failures and the original AST golden audit
remain unresolved. Final-source platform acceptance is recorded in the draft
PR's own CI, not copied from PR55. Draft/HOLD; no delivery promotion or release.
