Pinned Icarus acceptance inventory and paired execution
=====================================================

The source pin is steveicarus/iverilog commit
``f45ffabed3212a106f01cb362ef42c5d293f4513`` (14.0 devel).
Icarus is a reference implementation. A difference is not an established
Verilator bug or an established reference bug until its semantics have been
independently reviewed. No selected batch certifies complete SystemVerilog.

Inventory
---------

Generate new metadata from an untouched checkout of the exact source pin::

    python3 ci/portable/icarus_inventory.py \
      --repo /path/to/iverilog --out /new/inventory

The generator uses the original Perl parser and VPI list-reader, verifies that
passive observation preserves their complete parser states, and captures the
original Python process_test options with native execution disabled. Every
tracked ivtest file must match its committed Git blob.

The Linux default denominator is 3850 scenarios: Perl 3028, Python 746 and VPI
76. The types are 3069 normal/VPI, 711 expected compile errors, 27 compile-only,
2 expected runtime errors, 21 expected failures and 20 not-implemented entries.
These categories must remain separate; 3850 is not a positive simulation count.
Optional strict, force-SV, PLI1 and backend-translation profiles have separate
contracts and are not certified by this default inventory.

The first 128 selection is independent of execution outcomes. It takes
``floor(i*N/128)``, for i from 0 to 127, from the ordered Perl-then-Python pool
of normal, source-existing selfchecking cases with only mapped generation and
define arguments. The pool has 2209 entries; the batch has 107 Perl and 21 Python
scenarios. The separately generated 256 selection contains every first-128
scenario. Excluded entries remain explicit UNRUN slots in the full inventory.

The recovery comparison records whether regenerated metadata matches the prior
recorded hashes. Matching the inventory or selection does not recover missing
old execution logs and adds no execution credit.

Paired execution
----------------

Build and install the pinned Icarus source in its own workspace prefix. Include
the backend and VPI modules, and the optional libbzip2 dependency required for
LXT. A previous missing LXT dependency caused an installation failure in
br_gh710b before SV execution; dependency failures are not language failures.
Build Verilator from a clean committed compiler/runtime checkout::

    python3 ci/portable/icarus_sweep.py \
      --pinned-repo /path/to/iverilog \
      --inventory /new/inventory/core-inventory.json \
      --select /new/inventory/first128-runtime-structural.json \
      --iverilog-prefix /path/to/installed-icarus \
      --verilator-root /path/to/built-verilator \
      --output /new/batch-results --timeout 120 --min-disk-bytes 4294967296

Only normal selfchecking Perl/Python contracts currently have adapters. VPI,
negative/compile-only contracts, combined diagnostic golds and unmapped options
remain explicit adapter gaps. An adapter gap is not a claim of unsupported SV.
The noconfig language generation maps exactly to 1364-2001-noconfig. Arguments,
top modules and runtime plusargs are retained in a translation ledger.

Each engine receives an isolated copy of every original tracked fixture,
preserving executable helper modes. Sources, golds and selfchecks are not edited.
The Perl output name remains vsim; Python uses work/a.out. Verilator compiles a
native model with assertions, timing and fourstate enabled, then builds with one
make job. The runtime quiet option suppresses Verilator's own summary only.

Every compile, native build, execution and original oracle has an actual wait4
receipt. A small shell exec keeps the observer's child PID while redirecting the
tool's stdout and stderr to separate unfiltered files. The ``invoked_argv`` field
records the tool arguments; the native receipt records the full exec launcher.
The control tests verify that the PID printed by the tool equals the wait4 PID.

Files ending in .stdout and .stderr are the original tool streams, with byte
counts and SHA-256 hashes. The .output.log file concatenates those streams for
diagnostic inspection; it is not an assertion about their original interleaving.
The observer's .log belongs to the launcher and may be empty. Python's unchanged
original oracle receives stdout only; Perl's unchanged no-gold oracle scans
compiler and runtime output. Model FAILED messages remain failures even when
the native exit is zero or the original oracle also accepts a PASSED line.
Compiler-warning source excerpts containing an unexecuted FAILED string do not
receive model-failure credit. Primary tool errors still fail even with exit zero.

Crashes, mixed ordinary errors and timeouts cannot be classified as purely
unsupported diagnostics. Every unresolved selected case makes the batch gate
nonzero. A fully passing selected batch still has full_suite_complete=false,
with the remaining default scenarios represented as UNRUN.

The complete reference-only Icarus run must be reported separately, including
its own NI, CE, CO, RE and EF categories. Each new candidate must name its exact
SHA and actual platform results; prior candidate passes are not inherited.

Subprocess controls
-------------------

Run the native control tests without an HDL simulation credit claim::

    python3 ci/portable/test_icarus_sweep.py

They exercise actual exits, a timeout, original stream selection, native PID
identity, evidence overwrite rejection, preserved fixture modes, exact language
mapping, mixed diagnostics, and the full denominator with unrun slots.
