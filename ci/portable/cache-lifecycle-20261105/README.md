<!-- SPDX-FileCopyrightText: 2026 Mafei -->
<!-- SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0 -->

# Bound completed regression compilation caches

PR57 run41983367784, Rocky job127098348672, failed from filesystem exhaustion
at 07:21 UTC. Generated PCH and assembly writes reported `No space left on
device`; later stage disk guards refused to launch. Its full decoded log is
preserved with SHA256
`1342939655e9769f02eadae94e66c61add08a4c4f3d0fbeb27f016e0c203ca11`.
Strict18 recorded 18 C++ build failures and 18 runtime UNRUN cases. finish9
could not start its required stages; the fixed128 container failed dependency
installation, and the fresh migration container lacked disk space too.
Those failures must not be replaced with a previous commit's semantic totals.

The explicit regression groups accumulated completed model PCH/object caches.
The largest group has40 drivers; completed earlier groups remained on disk
while later groups compiled. After each group process exits, require a normal
completed harness summary with no Left/Running workers and a complete selected
count before reclaiming that group's compilation caches. Signal exits and
incomplete summaries retain all files and record incomplete infrastructure.
A complete FAILED summary may be reclaimed without altering its failed status.

Reclamation is confined to the selected `obj_vlt/t_NAME` directories. It uses
generated makefile/prefix/header/source evidence to identify rebuildable model
PCH/object files and retained runtime sources for runtime objects. Unknown
objects are retained. Directory/file symlinks are not followed; no permissions
or ownership are changed. Models, original and generated sources, logs, waves,
statistics, coverage, `.a` archives, `.d` dependencies and audit files remain.
This does not disable PCH generation or reduce test coverage.

An independent ledger records the selected group, reclaimed paths and byte
counts. Filesystem failures preserve the partial deletion ledger and propagate
as infrastructure exit2, while original harness exit codes/counts/success
remain unchanged. Both the independent result checker and typed artifact
producer require this ledger and reject incomplete or failed reclamation.
All selected groups remain recorded even after a failure.

The existing `--driver-prune` mode is intentionally unused because it also
removes executable models and other evidence. The fixed Icarus sweep already
reclaims successful case scratch space; its oracle, inputs and failed-case
records are unchanged. This candidate addresses the observed accumulation in
the main grouped regression runner only.

Compiler/runtime sources, original gold, semantic/reference classifications,
all564 driver identities and50 groups are unchanged from PR57. Native tests
may reuse its explicitly identified unchanged compiler; formal platform CI
must verify this candidate's own final commit. Earlier PR56/PR57 runs are
preserved and are not retriggered. Draft/HOLD; no delivery promotion or release.
