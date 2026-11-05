<!-- SPDX-FileCopyrightText: 2026 Mafei -->
<!-- SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

# Let the assertion-control stimulus complete before finishing

The original `assert_ctl_arg` stimulus enables concurrent assertions at time20,
then immediately calls `$finish` on the same rising clock edge. Its expected
output includes six pending concurrent assertion actions after the completion
marker. A model that terminates at the finish request does not execute them.
The original stimulus and its failure remain independently identifiable in
PR55 and PR56. Its exact input is preserved in `original/t_assert_ctl_arg.v.txt`
(SHA256 `2ab1d0cfb88cbbc865261680847bdb4140a17373c26eb82fa7b79fe07c347d3c`).

Delay the final finish request by one global precision step, using the single
delay-controlled statement `#1step $finish;` on the same source line. This lets
the pending time20 assertion actions complete; the existing C++ driver toggles
the clock once per precision tick, so the extra tick is a falling edge rather
than another assertion-sampling rising edge. Assertion controls, expected
output, exact coverage comparison and C++ harness remain unchanged.

This is a stimulus correction, not a compiler or finish-semantics change.
The original failing stimulus is not reclassified as passed, and execution
after an actual finish request is not restored. An isolated prototype on the
PR55 compiler matched all416 normalized expected output lines and all153
coverage lines, including the six formerly absent action reports. The final
tracked candidate must verify the unchanged complete output and coverage,
including inline/no-inline and related assertion/finish controls.

Compiler/runtime sources and all other test identities and expected files
are identical to PR56. Native verification may reuse its explicitly identified
compiler; the final candidate's own Actions rebuild and verify both platforms.
All original AST/trace audit failures and reference differences remain held.
Draft/HOLD; no delivery promotion or release.
