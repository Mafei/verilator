# Fixed-array reference arguments

<!-- SPDX-FileCopyrightText: 2026 Mafei
     SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

The native observations below are historical evidence for PR51, based on
implementation commit `93a84cf3` and final documentation commit `921b8562`.
The later [lifetime reference fix](../life-ref-20261104/README.md) records its
own results without rewriting these original observations.

This candidate replaces statement cloning for direct whole fixed-array element
arguments with a checked reference accessor. Valid arguments alias the original
element. Invalid arguments use separate caller-owned storage, reset on each
access. Basic numeric four-state components retain their all-X defaults.

The original `t_assoc` input is unchanged. The new two-state and four-state
drivers execute 997 and 1162 checks, including repeated invalid access, aliasing,
wide values, strings, receiver/index side effects, and valid nested/member
controls. The portable selection retains all 509 previous identities and
appends the 14 missing directed drivers, for 523 total.

After building, run the two public behavior drivers:

```sh
cd test_regress
python3 driver.py --vlt -j2 --no-skip-identical \
  t/t_assoc_ref_bounds.py t/t_fourstate_assoc_ref_bounds.py
```

`review.json` records source hashes and native precommit evidence. Commit-bound
native replay and Actions results are reported separately in the draft PR.
Native results do not establish macOS, Rocky or GLIBC 2.28 acceptance.

The old `select_bound_side_effect` statistics contract is preserved verbatim in
`../legacy/select-bound-ref-20261104/`. Its model still succeeds, while the old
one-else assertion fails after the implementation change. The active driver now
strictly requires zero cloned else branches and one checked-reference site.
It retains the original SV input and behavior assertions. An initial replay
that accidentally selected the active same-name driver is explicitly invalid
legacy evidence in the archive manifest.

The standalone probes keep independent limitations visible:

| Probe | Native baseline and candidate observations |
| --- | --- |
| `assoc_inout_min.sv` | Internal error before the fix; compiles after it. |
| `logic_ref_control.sv` | Baseline fails; candidate verifies four all-X reads and unchanged mixed-X/Z elements. |
| `ref_2d_control.sv`, `ref_struct_member_control.sv` | Valid global/class/member controls pass on both. |
| `alias_explicit_control.sv` | Return-left remains 17 while the aliased element is 18 on both; unresolved optimizer issue. |
| `signed_assoc_control.sv` | First signed key remains 0 instead of -5 on both; unresolved ordering issue. |
| `alias_external_control.sv` | The baseline rejects non-inlined ref functions accessing external state with IMPURE. |
| `runtime-bounded-cxx14-v1.cpp` | Native C++14 component has 26 checks plus size/alignment assertions. |

Wrapped/nested selector handling is retained. Mixed packed-struct and broader
composite invalid-reference defaults are not established. Strict18, fixed128,
their original oracles, and pending golden/classification decisions remain
unchanged. The delivery branch remains on HOLD.
