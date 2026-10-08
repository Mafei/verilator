# Experimental four-state builds

The `fourstate-upstream-20261008` branch additionally merges the official
`verilator/verilator` master commit
`4a2989705657d506d50dee5772bc17b3f689d9d5`, retrieved on 2026-10-08 UTC.
Its first parent retains the previously validated `fourstate-portable` commit
`d565afb615e3393970d6ce030d75df68b594e6b8` as a rollback baseline.
Cloud validation records the selected names and actual counts for 21 four-state
regressions and 26 upstream regressions in `out/regression-results.json`.
An additional four-state coverage compilation checks integration with the
official declarative toggle-coverage AST node.
The upstream group covers arithmetic shifts, memories, structures, classes,
parameters, interfaces, sampled sensitivity, processes, forks and timing.

This fork starts from Antmicro `dev/fourstate` at
`dbb8aedaa478389639295e40f16dbc7183d10b48` and merges
`feature/4_state_logic` at `5e132f32db577b3d596b66ce6378ac224ffa38d3`.
Both commits remain ancestors. Their Git merge base is
`c878a7e73523154a4f7da52bde9633d05b715c56`.
The core implementation was compared against the first dev four-state squash,
`d94a081499a972630c420d9ea3400ced77645c81`, as a content reference to reconcile
independently squashed copies, without changing Git ancestry.

## Integration decisions

- Retain dev's aggregate types, dynamic arrays, complex pins, modports,
  `$isunknown`, `$sampled`, count operations, formatting, and paired VPI storage.
- Adopt feature's temporary ownership handling, top-level port metadata,
  64-bit trace comparison fixes, corrected VCD X/Z encoding, new FST writer,
  and its newer upstream compiler/runtime changes.
- Continuous-driver conflict registration is currently disabled, including
  simple nets. Bus contention and drive-strength resolution remain experimental
  limitations and require explicit semantic tests before they can be enabled.
- Route paired public variables through residual VPI registration rather than
  the newer value-only table; preserve X/Z comparisons in value callbacks.
- Preserve dev four-state test fixtures and feature generic JSON fixtures.
  The obsolete feature formatting-unsupported test is removed because dev's
  formatting implementation preserves X/Z; the decimal, binary, octal and hex
  output tests validate that behavior. `LOGICCAST` remains a warning alias for
  feature's `CASTFOURSTATE` name.
  A successful focused CI run does not certify the entire upstream regression
  suite or complete IEEE four-state semantics.

The GNU Flex signature adjustment removes OS-version guessing in `src/flexfix`.
It was previously verified in the authorized SS-OCT experiment; only this public
Verilator patch is reused, with SHA256
`799d300562094b602d559eecc18d0742f8e393a1ff96480d3d3cb8992735654b`.
No private application models or project files are included.

## Platforms and artifacts

Source development, compiler builds and regression simulations run in the Linux
cloud workspace. No developer Mac needs to be online. Formal portable packages
are built in GitHub Actions on pushes, pull requests, or manual dispatch.
The macOS target is ARM64 (`macos-26`, checked with `uname -m`). The Linux target
is x86-64 Rocky Linux **8.10**, built inside its distribution container using
GCC toolset 13. The official container is pinned to x86-64 image digest
`sha256:f5529992e67440c1a4ae7788244d4381c6909159a88eacd95b7523ae47ced82e`.
The compiler statically links libstdc++ and libgcc while keeping
the system glibc dynamic; CI checks that its GLIBC symbol requirements do not
exceed 2.28 and that every shared library resolves. Generated timing models
require a C++20-capable compiler (GCC 13 or a suitable Clang).

GNU Flex 2.6.4 and Bison 3.8.2 are built from HTTPS archives with pinned SHA256
hashes. The matching GNU `FlexLexer.h` is selected explicitly. Optional allocator
libraries and CPU-specific `-march=native` optimizations are not used.
Flex is configured with `CPPFLAGS=-D_GNU_SOURCE` so glibc 2.28 declares
`reallocarray`; otherwise Flex 2.6.4 can truncate its return pointer and crash.
FST model generation also requires LZ4 and zlib development headers and libraries.
CI installs these dependencies on the cloud runners.

Artifacts contain the optimized compiler, Python/Perl scripts, runtime headers
and sources, generated make metadata, CMake/pkg-config data, examples, licenses,
provenance, dependency reports, and checksums. Debug/coverage executables are
not included. Unpack anywhere and invoke `bin/verilator`; leave `VERILATOR_ROOT`
unset to use the relocated installation's own runtime files.

CI checks the relocated package by compiling and executing a four-state timing
model, including a required failure on an unknown comparison. The Linux package
is tested in a new Rocky 8.10 container with a different installation path.
Published artifacts are development snapshots, not releases.

## SystemVerilog capability checks

The `fourstate-sv-20261008` candidate adds four capability regressions and
nineteen inherited four-state regressions to the upstream candidate's 48 checks,
for 71 explicitly selected checks. The result gate requires every selected
group, its original log, actual counts, process exit code and commit provenance
to agree. A partial group set, skipped tests, retry failures or a mismatched
commit fail validation. The gate's independent failure fixtures also run with
macOS Bash 3.2.

| Area | Public regression evidence | Scope and remaining limits |
| --- | --- | --- |
| Arithmetic and logical shifts | `t_fourstate_shiftrs` executes 9,832 checks using 7/31/48/65/95-bit data, widened results, 65-bit distances, X/Z signs and counts, and operand side effects. | Value and X/Z halves share one operand evaluation. The test drives its own clock and checks its execution count. |
| Fixed unpacked integral RAM | `t_fourstate_mem_index` checks unknown, high-bit, invalid, signed, ascending and multidimensional addresses; blocking/NBA writes; function indices/RHS effects; and integral class-member elements. | Address snapshots are scoped to their owning statement. Whole-subarray assignments and invalid dynamic-array accesses remain outside this guarantee. Very wide index normalization needs further reference-simulator comparison. |
| Unknown detection | `t_fourstate_isunknown` and the RAM/shift capability checks exercise `$isunknown`, including expressions with side effects. | Replacement expressions must retain their state classification and evaluation effects. `int`, `byte`, `shortint` and `longint` are two-state types; unknown-address tests use four-state `logic` addresses. |
| Behavioral arithmetic model | `t_fourstate_mac_model` simulates signed 18-by-27-to-48 multiply/add/shift, enable, synchronous reset and delayed global reset. | This independently written model does not certify DSP48E2 parameter modes, cascades, control words, timing checks or the vendor `glbl` implementation. |
| Supply nets | `t_fourstate_supplies` simulates constant `supply0` and `supply1` vectors. | Constants do not validate drive strengths, pullups/pulldowns, `tri0`/`tri1` or bus contention. |
| Complex assignment and ports | The inherited complex-assignment and complex-pin tests execute X/Z checks and receiver side-effect assertions. Streaming assignments use a positive runtime test. | General multi-driver, UDP, switch, specify and strength resolution remain limited. Continuous-driver conflict registration remains disabled. |
| Coverage and activity output | The coverage integration case executes array-input and compound-assignment assertions. The separate SAIF regression checks its existing 1-to-301-bit output after removing a duplicate emitter. | Toggle counts and unpacked-struct coverage are not certified. SAIF X/Z residence times and close-time transitions still need correction; its current golden output is not a full four-state activity oracle. |

Compiler success alone is not accepted as capability evidence. These tests
simulate and check values; the selected VCD/FST regressions additionally compare
waveforms. The matrix describes specific tested behavior, not complete
SystemVerilog support. Only public minimal tests and existing public patches are
used; restricted vendor models and private RFSoC applications are not included.

The broader four-state suite is also audited. Its multi-driver VCD/FST demo
currently produces incorrect contention and wired-OR values, independently of
the passing single-driver trace regressions. Unsupported-feature diagnostic
fixtures and old compile-failure expectations also need migration after the
official merge. These failures prevent treating the whole suite as green or
the candidate as ready to replace the portable baseline.

For cloud development, run `ci/portable/run_regressions.py` with the selected
group names directly, without setting an Actions environment variable. The
same count and provenance gate applies. `ci/portable/sync_upstreams.py` audits
Veripool master and both Antmicro branches, records observations and can create
an isolated merge candidate. It does not push or advance the delivery branch;
the existing scheduled upstream check remains the only recurring task.

The manual `Original four-state baselines` workflow builds both original commits
with the same Rocky toolchain and runs a common scalar and aggregate probe.
Only the public test harness and GNU Flex header adjustment are copied into
these checkouts. Results and the exact source adjustment are uploaded as evidence.
