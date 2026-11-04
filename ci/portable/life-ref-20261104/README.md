# Reference aliases in lifetime optimization

<!-- SPDX-FileCopyrightText: 2026 Mafei
     SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

Two reference formals can name the same object. For example, after `left = 17;
right = right + 1; return left;`, a call with the same valid element for both
arguments must return 18. The previous compiler returned 17 while the element
itself was 18. It also removed an earlier write that a `const ref` alias should
observe before a later write.

The lifetime pass recorded constants and removable assignments independently
for each formal. The fix records complex-write and consumed-read history for
`ref` and `const ref` formals, without retaining those independent facts.
Ordinary local-variable optimization is unchanged.

The new drivers execute 192 two-state and 288 four-state checks over eight
iterations. They cover same and distinct actuals, return-left, intermediate
reads through `const ref`, reverse writes, branches and 65-bit mixed known/X/Z
data. The existing `opt_life` driver retains its exact 5/5/1 statistics.

After building, run the behavior and optimization controls:

```sh
cd test_regress
python3 driver.py --vlt -j2 --no-skip-identical \
  t/t_opt_life_ref_alias.py t/t_fourstate_life_ref_alias.py \
  t/t_opt_life.py t/t_opt_life_off.py
```

`review.json` preserves source-bound native red/green observations. The original
[public alias probe](../assoc-ref-20261104/probes/alias_explicit_control.sv)
is unchanged. Its failure at PR51 remains recorded; the later prototype and
the `-fno-life` control both satisfy the same assertions. Commit-bound replay
and platform results are reported separately in the draft PR.

The portable selection retains all 523 previous identities and their group
order, then appends six drivers, for 529 identities in 46 groups. The original
438 projection and old clocking failures remain separately audited.

Dynamic `const ref` array selections can still be rejected before lifetime
analysis; the new const-reference cases use supported direct variables with
the existing no-inline annotation. Signed associative-key ordering and other
previously recorded limitations are outside this fix. Original output goldens,
Strict18/fixed128 oracles and classifications remain unchanged. Native results
do not establish ARM64 or GLIBC 2.28 acceptance. The candidate remains on HOLD.
