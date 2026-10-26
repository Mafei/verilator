Four-state and SystemVerilog verification scope
==============================================

This candidate is an incremental open-source simulator integration. It does not
certify complete SystemVerilog or a complete vendor simulation library. The
implementation boundaries below must be read together with the regression
results for the exact committed compiler/runtime SHA. A named test is a
verification contract, not evidence that it ran on a different candidate.

``supported`` means the bounded behavior named in that row is implemented.
``partial`` identifies additional known boundaries. ``unsupported`` means an
explicit compiler diagnostic is required. ``untested`` means no corresponding
model acceptance is claimed. Runtime checks, expected-diagnostic checks,
execution controls and reference-only tests are counted separately.

.. list-table:: Capability boundaries
   :header-rows: 1
   :widths: 19 12 42 27

   * - Domain
     - Status
     - Bounded behavior and limits
     - Public verification contract
   * - Language selection
     - supported
     - 1364-2001-noconfig keyword mode, command-line precedence and nested keyword blocks.
     - t_flag_language_noconfig and its bad profile
   * - Packed four-state storage
     - partial
     - Value/XZ storage and public API projections; no general aggregate or class certification.
     - fourstate_portable, fourstate_api, fourstate_packed_array
   * - Scalar reductions
     - supported
     - All six reduction operators preserve X/Z scalar semantics, including typedefs and captures.
     - fourstate_reduce_scalar: 1094 checks
   * - Equality and wildcards
     - partial
     - Known mismatches dominate wildcard unknowns; mixed case equality checks the whole XZ mask.
     - fourstate_wildcard: 2570; fourstate_case_equal_known: 144
   * - Arithmetic and signed shifts
     - partial
     - Public signed arithmetic/shift tests through non-word-aligned widths; pessimistic unknown propagation.
     - fourstate_arithmetics, fourstate_shiftrs, math_shift family
   * - Unknown predicates
     - partial
     - Packed values and memory-selection predicates, including two-state results with four-state operands.
     - fourstate_isunknown, fourstate_sen_expr
   * - RAM reads and indices
     - partial
     - Public bounds/unknown-index checks and six-lane RAM matrix; not vendor RAM timing or collision modes.
     - fourstate_mem_index, fourstate_array_guard; ram_acceptance.py
   * - Indexed packed part-select reads
     - partial
     - Signed and unsigned domains through 95-bit indices, partial overlap, shifted/ascending declarations and +:/-: coordinates. Carry arithmetic preserves the existing index diagnostics. Existing bit-selection and write lowering remain separately bounded.
     - fourstate_slice_index_domain:3840 checks,80 literal reports,64 complete histories; slice_packed_domain:98 checks,24 reports,4 histories; slice_index_width and bad profiles
   * - Clipped partial writes
     - partial
     - Negative/overlapping/full-outside writes, signed/unsigned wide indices and X/Z suppression. W4 variable +:33 is included directly, without a narrower-width exception.
     - timing/fourstate_nba_partselect_clip and nba_clip_bounds
   * - Memory file I/O
     - partial
     - Public read/write, range and expected-error profiles; not every external file format.
     - readmem regression group
   * - NBA snapshots
     - partial
     - RHS, target and index snapshots, delayed task controls and official time-zero non-inlined task repair.
     - nba and sv_controls_20261012; nba_noninlined_await
   * - Repeat event controls
     - partial
     - Packed blocking/NBA counts evaluated once, zero/negative/XZ counts and wide counters. Repeat event triggers/procedural assign remain explicit unsupported cases. Mutually interacting NBA operand side-effect order is not certified.
     - timing/fourstate_nba_repeat_control; timing_nba_repeat_unsup
   * - Sensitivity and iff
     - partial
     - Pure indexed/conditional expressions, XZ/edge changes and known-one iff truth. Captures are private to each generated CFunc invocation. Impure source cases are rejected explicitly.
     - fourstate_sen_expr:61; sen_iff:36; sen_hierarchy:258, threads2
   * - Four-state wait predicates
     - partial
     - Reduction predicate reevaluation has an independently reproduced failure; it is not a supported acceptance result.
     - known-gaps/wait_fourstate_reduction.sv
   * - Dynamic arrays
     - partial
     - Positional/keyed/default constructors, size/value calls once and independent XZ copies. Other aggregate methods require their own acceptance.
     - fourstate_cons_copy:15; cons_keyed:16; dynarray profiles
   * - Queues and casts
     - partial
     - Two-state elements, construction/splicing and explicit XZ-to-bit conversion; no general XZ queue storage claim.
     - fourstate_cons_queue:13; queue regression profiles
   * - Structures
     - partial
     - Packed fields and unpacked bit fields; unpacked XZ fields remain unsupported.
     - fourstate_struct; cons_struct:8; cons_unpacked_unsup diagnostic
   * - String literals and byte arrays
     - partial
     - Fixed unpacked byte literals fill from the declared left bound with zero padding/truncation; packed integral casts retain right alignment. Nonzero/negative bounds and signed/unsigned byte typedefs are covered. Dynamic string-to-container casts are not certified.
     - string_unpacked_literal:78 checks; string_byte:8 strict checks corrected to IEEE1800-2023 5.9, with the prior test and conflict logs preserved
   * - Ancestor task/function lookup
     - partial
     - Per-instance ancestor lookup remains an unresolved binding gap. A shared task pointer cannot safely represent different parent-instance definitions; no generic parent fallback is claimed.
     - Pinned sv_task_call_instance_lookup remains a compile failure in fixed128
   * - Resolved nets and supplies
     - partial
     - Public supply/pull/default/inout, multi-driver and procedural-enable profiles. Complex strengths and hierarchical cases retain explicit boundaries.
     - resolve, pull, supplies, tri_storage_20261026; *_unsup
   * - Force, release, deassign
     - partial
     - Public packed/net/process cases only; no general analog resolution model.
     - force_packed_release, fourstate_force_release, deassign group
   * - Finish, final and processes
     - partial
     - Original finish9 outputs and complete histories remain mandatory; legal race/ordering boundaries are not silently rewritten.
     - finish_acceptance.py, finish and process regression groups
   * - VPI, tracing and interfaces
     - partial
     - Public packed-member XZ registration, native VPI controls, bounded interface and full-history VCD/FST checks. Not all public VPI entrypoints are implemented.
     - fourstate_vpi, VPI upstream groups, trace and thread controls
   * - DSP48E2 and glbl models
     - untested
     - Public independent MAC/reset behavior is tested separately. Full vendor DSP48E2/glbl libraries and restricted RFSoC/SS-OCT models are not included or certified.
     - fourstate_mac_model is a behavioral subset, not the vendor model

Acceptance accounting
---------------------

The original 297 native regression selections remain present, with additional
candidate/official controls. The exact unique names and counts come from
``run_regressions.GROUPS`` and ``run_thread_controls.NAMES``. The checker rejects
nonzero subprocesses, retries, missing/duplicate passes, skipped selections and
missing final summaries. Golden files are generated by the original harness.

Pinned Icarus f45ffabed3212a106f01cb362ef42c5d293f4513 is a reference
implementation, not a replacement for independent language semantics. Its
original default inventory has 3850 scenarios: 3069 positive runtime, 711 CE,
27 CO, 2 RE, 21 EF and 20 NI. The fixed 128 pair retains 3722 UNRUN slots and
full_suite_complete=false. Unsupported cases and unresolved differences keep
that pair's real gate nonzero. No reference fixture/gold is modified.

An unsigned 32-bit all-ones index remains 4294967295 even when the packed
declaration includes negative indices. The slice-bounds once-evaluation control
checks this out-of-range read separately from an explicit signed -1 call. Pinned
Icarus instead treats both as -1 in the independent negative-bound probe; this
reference difference remains recorded. The exact new packed-word fixture also
triggers a pinned-Icarus elaborator assertion, so no reference runtime acceptance
is claimed for that fixture. These are separate from the immutable fixed128 and
Strict18 inputs and expectations.

The legacy strict18 original-output gate is reported separately from the
applicable16 gate, and its nonzero result propagates to the build exit. Earlier green jobs with full18_gate_exit=1 are not accepted
as an 18/18 success. Formal macOS ARM64 and Rocky8.10/glibc2.28 results must
name the exact final SHA, native exits, output/wave hashes and package hashes.
