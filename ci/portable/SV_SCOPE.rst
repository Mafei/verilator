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
   * - Packed element and indexed part-select reads
     - partial
     - Signed and unsigned domains through 95-bit indices, partial overlap, shifted/ascending declarations and +:/-: coordinates. Carry arithmetic preserves the existing index diagnostics, including packed-element multiplication and nested selection without 32-bit offset wrap. Scalar bit-selection and write lowering remain separately bounded.
     - fourstate_slice_index_domain:3840 checks,80 literal reports,64 complete histories; slice_packed_domain:98 checks,24 reports,4 histories; nested_select:34 checks,8 reports,4 histories; slice_index_width and bad profiles
   * - Clipped partial writes
     - partial
     - Negative/overlapping/full-outside writes, signed/unsigned wide indices and X/Z suppression. W4 variable +:33 is included directly. Signed offsets through supported unpacked bit-struct and class-array fields retain NBA index snapshots; this does not certify unpacked XZ structures. Runtime boundary insertion uses word-wise C++14 operations.
     - timing/fourstate_nba_partselect_clip, nba_clip_bounds; fourstate_struct_select:1088 checks across widths7/15/31/33/65/95
   * - Runtime insertion portability
     - partial
     - C++14 scalar and word-wise insertion with clipped edges, zero extension and exact same-base buffers. Arbitrary overlapping offset pointers and extreme declaration/index normalization remain outside this acceptance.
     - runtime_insert.cpp:3296 independent bit-oracle checks; native UBSan and relocated-package smoke
   * - Memory file I/O
     - partial
     - Public read/write, range and expected-error profiles; not every external file format.
     - readmem regression group
   * - NBA snapshots
     - partial
     - RHS, target and index snapshots, delayed task controls and official time-zero non-inlined task repair.
     - nba and sv_controls_20261012; nba_noninlined_await
   * - Postponed monitors
     - partial
     - Once-per-time-step final values and queued monitoron requests, including X/Z and 129-bit arguments. Disabled registration differs from pinned Icarus by an additional OFF14 report; that reference difference remains open. Multiple instances sharing one source monitor site are not certified.
     - timing/fourstate_monitor_postponed:19 checks each; official sys_monitor_changes; all original gold retained
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
     - Two-state elements, construction/splicing, bounded-assignment truncation and slices, and explicit XZ-to-bit conversion; no general XZ queue storage claim. The official bounded-queue warning/output contract is retained.
     - fourstate_cons_queue:13; queue_bounded, queue_slice and other queue regression profiles
   * - Type comparisons
     - partial
     - The integrated official implementation covers matching predefined integer/vector types in constant type() comparisons. The public test includes signedness, widths, dimensions and generate-time selection; this row does not certify every class or aggregate type relation.
     - type_compare; original upstream assertions remain unchanged
   * - Structures
     - partial
     - Packed fields and unpacked bit fields; unpacked XZ fields remain unsupported.
     - fourstate_struct; cons_struct:8; cons_unpacked_unsup diagnostic
   * - String literals and byte arrays
     - partial
     - Fixed unpacked byte literals fill from the declared left bound with zero padding/truncation; packed integral casts retain right alignment. Nonzero/negative bounds and signed/unsigned byte typedefs are covered. Dynamic string-to-container casts are not certified.
     - string_unpacked_literal:78 checks; string_byte:8 strict checks corrected to IEEE1800-2023 5.9, with the prior test and conflict logs preserved
   * - Packed format destinations
     - partial
     - $sformat/$swrite write known character bits and clear X/Z masks of whole packed variables, including task-local buffers, typedef widths29/95/129 and simple packed structs. A destination used as a format input retains its old mask until formatting completes. Two-state bit/string paths have separate controls. Four-state selected, array-element, object-member and concatenation destinations remain unsupported. Separate fourstate_format_trunc C++14/two-state/four-state controls cover packed suffix truncation and partial-byte masking; real default field widths and file-I/O conversion behavior are outside this change.
     - fourstate_format_packed:50 assertions across7 profiles; fourstate_format_trunc:182 checks (146 C++14 runtime,18 default two-state,18 four-state)
   * - Dynamic real decimal formats
     - partial
     - Runtime decimal formatting uses the existing rounded signed-64-bit representation without accessing an integral XZ mask. Finite values in the signed-32-bit range, explicit minimum/eight-column fields, two string-output APIs, a whole packed destination and following real/integer arguments are covered in C++14 without timing. This does not specify a new default field width or certify NaN, infinity or out-of-range conversion.
     - fourstate_format_real:39 literal checks in each of four two-state/four-state and explicit-width profiles
   * - Explicit variable import visibility
     - partial
     - Definition-site views preserve direct explicit package-variable imports in source-qualified module, function, block, foreach and generate scopes, including parameter clones and repeated includes. The complete module and query-role closure must qualify; wildcard/export, type, port, cell/member and other unclosed roles retain the prior implementation and an eligibility reason. This does not establish complete package import support or repair the remaining original import matrix failures. Ordinary module forward visibility is retained as a fork baseline; the pinned Icarus rejects the new combined fixture's later variable references, so its 25 checks are single-engine evidence, not a paired standard certificate.
     - import_context_capture checks the source ledger; package_import_lexical checks 25 values and eligibility metadata. The original fixed128 package-import/foreach case and the original import matrix keep their exact sources, flags and oracles and require fresh candidate results.
   * - Ancestor task/function lookup
     - partial
     - Static runtime tasks use instance-specific ancestor bodies and state in unparameterized static module cones, with nearest-task selection and fixed packed integral input/output formals. Parent parameters, generates, arrays of instances, recursion, hierarchy/serialization modes, source package imports/exports in the affected cone, ancestor functions and complex/default/ref/inout formals remain explicit unsupported boundaries. Mixed nearer non-subroutine names are rejected as an implementation boundary, without classifying the source as invalid. Ordinary missing names retain their diagnostics and suggestions. This is a bounded task subset, not complete task/function or SystemVerilog support.
     - func_ancestor_ctx:15 literal checks per two-state/four-state profile; func_ancestor_xz:30 four-state XZ argument/output/state checks and30 on the exact pinned-Icarus fixture;6 diagnostic gold controls. Historical fixed128 inputs/results are preserved and require a fresh full candidate run.
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

The three positive constraint_rand_sampler/default/solver profiles are ``NOT_RUN_missing_solver`` and excluded from strict counts; only the two sampler bad/env_bad diagnostic profiles are selected while no solver is available.

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
