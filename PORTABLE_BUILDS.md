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

The job log prints the optimized compiler's SHA256 immediately after its build.
After validation it also prints every `out/SHA256SUMS` entry, including the
portable tar package. The checksum file excludes itself so repeating this step
does not create a self-referential digest. Debug enum evidence records the raw
generated identifiers and both raw and normalized SHA256 values for each
`t_debug_emitv` width dump. Normalization replaces only its eight-digit enum
type hash, preserving distinct type identities, repeated references and numeric
suffixes. The raw width dumps remain in the existing artifacts. A cloud checkout
with those dumps can reproduce the log with
`python3 ci/portable/log_evidence.py results`; it requires no download token or
additional toolchain dependency.

CI checks the relocated package by compiling and executing a four-state timing
model, including a required failure on an unknown comparison. The Linux package
is tested in a new Rocky 8.10 container with a different installation path.
Published artifacts are development snapshots, not releases.

## SystemVerilog capability checks

The `fourstate-sv-20261008` candidate adds four capability regressions and
nineteen inherited four-state regressions to the upstream candidate's 48 checks,
for 71 explicitly selected checks. The next bounded follow-up adds fifteen
case, numeric conversion, timing, queue, interface, member, JSON, pull-default
and SAIF checks, for **86 explicitly selected checks**. Existing checks retain
their names. Compiler invocations use `--no-skip-identical` so a prior generated
model cannot certify a different compiler binary. The result gate requires
every selected group, its original log, actual test names and counts, process
exit code and commit provenance
to agree. A partial group set, skipped tests, retry failures or a mismatched
commit fail validation. The gate's independent failure fixtures also run with
macOS Bash 3.2.

The `fourstate-readmem-20261008` candidate preserves those 86 checks and adds
an independent `readmem` group of 16 checks, for **102 explicitly selected
checks**. Two new public four-state positive tests target integral memory-file
loading and address ranges. A runtime-negative driver checks malformed input
and range diagnostics, while a compile-negative driver checks retained
unsupported memory types and shapes. Twelve unmodified upstream checks cover
hexadecimal/binary reading and write/read round trips, wide and aligned elements,
associative arrays, EOF without a newline, malformed addresses and digits,
short or missing files, and unsupported associative-array types. These use their
original sources and goldens. In particular, the historical name
`t_sys_readmem_4state` denotes a compatibility test of two-state random-reset
behavior; it is not evidence of preserved X/Z data. The readmem checkpoint
passed all 102 selected checks on Linux cloud, macOS ARM64 and Rocky Linux
8.10 at `0ae4471d1bd0db9c0b1cdf31a500b66f8502615a`. That checkpoint remains
preserved. This selection does not establish support for all memory types or
original vendor RAM models.
Range inputs are committed `.mem` files; the width and runtime-negative drivers
generate their inputs beneath `TEST_OBJ_DIR`. All drivers retain the forced
generation option and their independent names, counts and exit-status checks.

The `fourstate-nba-20261008` candidate retains all 102 checks and adds
an independent `nba` group with 23 executable checks, for **125 explicitly
selected checks**. Nineteen unchanged upstream drivers exercise delayed
assignments, dynamic and deep array references, packed partial updates,
forks, waits and disable-fork behavior. Two new independent drivers compare
two-state and four-state delayed packed updates at 7/33/65/95/129 bits, including
RHS/index side effects, repeated clocks, nested forks, word-boundary selects and
same-writer ordering. They check execution counts, values, update times and
eleven exact VCD histories per driver. A third new driver independently checks
packed-vector change events, X/Z-only changes, repeated values, mixed sensitivity
and LSB edge controls. An independent time-observer test uses blocking updates
without NBA queues and checks `$time` and fractional `$realtime` event bodies.
The original readmem checks and failure-propagation gate remain part of the
same selection.

The `fourstate-pull-20261008` candidate preserves all 125 selected checks and
adds an independent `pull` group with a positive simulation and a compile-negative
driver, for **127 explicitly selected checks**. The positive driver checks 4,036
values, event counts, snapshots and time observations, plus 120 exact VCD
histories. It exercises single whole continuous drivers of local `tri0` and
`tri1` packed vectors at 1/7/33/65/95/129 bits, ascending and nonzero ranges,
mixed X/Z data, repeated values, release to Z and subsequent driving. Separate
65-bit RHS signals in the same module check that different assignments retain
independent captures. The compile-negative driver checks fourteen unsupported
driver contexts against native compiler-generated diagnostic goldens.

Four additional constant-driver assertions and their exact scalar VCD histories
retain the known-driver path. They also reproduce an inherited scalar trace
defect: a generated one-bit expression can carry upper storage bits into the
four-state character lookup. The shared scalar trace path masks both halves
to their low signal bit before recording and emitting a value; change detection
also ignores storage padding. This keeps the VCD/FST/SAIF trace interfaces within
their single-bit input range without changing two-state tracing.

The bounded pull fix snapshots both value and X/Z halves before writing either
target half. Only released Z bits receive the implicit pull value; active X
bits remain X. This applies to one default-strength, untimed, whole continuous
driver of a local four-state packed integral net. Hierarchical RHS reads and
input-pin consumers are allowed. Multiple drivers, partial or hierarchical
writes, output/inout/ref pin drivers, aliases, force/release or external write
access, net or assignment delays, explicit driver strengths, and impure
continuous RHS expressions remain outside
this implementation and receive an unsupported diagnostic. Eligibility requires
a compiler-classified pure RHS expression; this is a conservative function
purity boundary, including static-local writes. Existing undriven
pull defaults and optimized known constant drivers retain their separate paths.
The fallback is never applied separately to multiple driver contributions.
An independently checked function that updates a nonlocal call counter causes
an inherited settle loop even when driving an ordinary wire. This candidate
rejects impure pull-net RHS expressions instead of claiming that broader
scheduling behavior is fixed. The selected tests do not certify arbitrary
function calls or general strength, switch and bidirectional-net semantics.
Existing four-state aggregate restrictions, including the explicit rejection
of packed union variables, also remain in place.

The `fourstate-resolve-20261008` candidate keeps all 127 pull-stage selections
and adds an independent `resolve` group with five drivers, for **132 explicitly
selected checks**. Four positive drivers target pair and triple drivers,
resolved-net events and input-default compatibility. A compile-negative driver
checks retained unsupported contexts against diagnostic goldens. The shared
public header and oracle helper
are tracked test inputs, not extra drivers. All groups retain forced generation,
exact unique test names, counts, exits and commit provenance. This candidate's
runtime and portable platform verification remain pending until their actual
logs have been checked.

The resolver accepts exactly two or three whole continuous assignments to a
local four-state packed integral `wire`, `tri`, `wor` or `wand`. Each contribution
has its own persistent value/XZ packet initialized to Z. One resolver owns the
result pair and reads every contribution. Assignments must have compiler-classified pure RHS
expressions, default equal strengths, and no net or assignment delay. Known
constant contributions stay part of resolution. Disjoint static partial writers
retain their existing path. For potentially overlapping multiwriter candidates,
overlapping partial writes, port/pin and hierarchical
writers, aliases, force/release, external write access, explicit strengths,
delays, impure RHS expressions and more than three contributions are rejected.
Implicit ANSI and non-ANSI output net declarations receive the same explicit
nonlocal-target diagnostic as `output wire`. This does not add port resolution,
bidirectional nets, switch primitives or general strength semantics.

A module input declaration default supplies an unconnected-port fallback. Its
synthetic static initializer is excluded from contribution counts; real
continuous and hierarchical writers remain subject to the same audit. Connected
inputs override that fallback for known, X and Z values.

The pair driver checks all sixteen 0/1/X/Z pairs in both declaration orders and
four net kinds at 1/7/33/65/95/129 bits: 768 primary checks, plus 384 known/dynamic
and 768 literal-constant checks. The scalar triple driver checks all 64 input
combinations in all six declaration orders and four net kinds: 1,536 checks.
The event driver checks 4,320 values, snapshots, event counts and time/realtime
observations, plus 476 packet checks at additional 17/24/31/32/63/64-bit storage
boundaries. The input-default driver adds 1,296 assertions at the six primary
widths with omitted, open and connected ports, including mixed X/Z, snapshots,
events and time/realtime. The four positive drivers total 9,548 runtime assertions
and 1,430 complete reference VCD histories, including the driven sources.
Seventeen compile-negative cases use native compiler-generated goldens. A
successful simulation completion marker does not bypass the value or waveform
oracle.

The harness emits each short `Self PASSED` record with both line boundaries in
one native write, below the POSIX minimum atomic pipe-write limit. This prevents
parallel compiler fragments from swallowing a record. The anchored result parser
still rejects an embedded marker. Native partial-prefix and competing-writer
fixtures exercise the real emitter alongside all existing failure controls.

The source histories exposed an inherited trace-activity gap before the first
suspension of a split coroutine. The bounded trace fix marks activity at entry
and retains the existing markers after each await; ordinary function handling
and the simulation scheduler are unchanged. Large-consumer resolver expression
growth remains a separate performance acceptance check. An additional independent
21,280-observation probe generated approximately 206 MB of C++ and exceeded its
300-second `--binary` build limit. Its already-generated C++ subsequently passed
an explicit make, runtime and strict waveform oracle, but the original timeout
remains a failed performance check. Successful small-model simulation alone does
not certify that check.

The delayed NBA loss also reproduces with an actual optimized build of the
unmodified official `4a2989705657d506d50dee5772bc17b3f689d9d5` baseline.
It is not introduced by the four-state integration. The bounded fix captures
each delayed assignment's RHS and target before its asynchronous fork, using
the existing by-value coroutine remapping, then preserves each pending packed
update in the existing commit queue. Zero-dimensional queues use standard
`std::array`, including strict C++14 builds; unpacked-array queues keep their
existing behavior. The fix does not certify arbitrary class targets, clocking
blocks or all NBA ordering cases. The separate, open upstream
[PR 8488](https://github.com/verilator/verilator/pull/8488) addresses a broader
NBA scope and remains a follow-up candidate rather than an automatically merged
dependency.

Original RAM probes also exposed an inherited four-state packed-vector event
defect: change detection inspected only bit zero. The bounded event fix reduces
all value/XZ bit differences for change sensitivity. `posedge`, `negedge` and
both-edge controls retain their LSB behavior. This event fix does not implement
continuous-driver resolution or driven-Z pull fallback.

An additional inherited optimization defect moved an explicit change-sensitive
process with a time-only body into initialization. It reproduces with blocking
updates and no NBA queue, in both two-state and four-state builds. The bounded
fix keeps explicit event sensitivity when the body reads `$time` or `$realtime`;
it retains their existing purity classification in other compiler passes.
Non-inlined temporal helper functions and broader implicit sensitivity remain
outside the listed direct-observer checks.

The four-state file reader keeps X and Z distinct, masks unused storage bits,
zero-extends short words, truncates oversized words with a warning, preserves
untouched entries and clears their X/Z masks when known data is loaded again.
Defaults traverse the declared numerical low-to-high bounds; explicit start/end
arguments select either direction. Sparse addresses use checked 32-bit hexadecimal
address tokens, including negative array indices encoded in two's complement.
Malformed digits, addresses and addresses outside the selected range are errors;
files that are missing, short or too long retain diagnostic handling.

This bounded implementation warns and performs no writes when a packed filename
contains any X/Z bit, an address contains X/Z, a known address is outside the
declared array, or an unsigned address cannot fit a signed 64-bit index. These
are explicit implementation policies, not certification of unknown-argument
conversion in SystemVerilog. In particular, the packed-filename policy also
checks unknown padding bits. Filename and bound expressions are captured once.
Existing two-state memory-file reading and writing retain their separate path.
Four-state conditional expressions also retain a selected Z branch instead of
being rewritten into logical operations that would turn it into X.

| Area | Public regression evidence | Scope and remaining limits |
| --- | --- | --- |
| Arithmetic and logical shifts | `t_fourstate_shiftrs` executes 9,832 checks using 7/31/48/65/95-bit data, widened results, 65-bit distances, X/Z signs and counts, and operand side effects. | Value and X/Z halves share one operand evaluation. The test drives its own clock and checks its execution count. |
| Fixed unpacked integral RAM | `t_fourstate_mem_index` checks unknown, high-bit, invalid, signed, ascending and multidimensional addresses; blocking/NBA writes; function indices/RHS effects; and integral class-member elements. | Address snapshots are scoped to their owning statement. Whole-subarray assignments and invalid dynamic-array accesses remain outside this guarantee. Very wide index normalization needs further reference-simulator comparison. |
| Unknown detection | `t_fourstate_isunknown` and the RAM/shift capability checks exercise `$isunknown`, including expressions with side effects. | Replacement expressions must retain their state classification and evaluation effects. Unknown-address tests use four-state `logic` addresses; coverage of integer atom types is limited to the listed regressions. |
| Fixed integral memory-file loading | `t_fourstate_readmem` and `t_fourstate_readmem_range` check `$readmemh`/`$readmemb`, X/Z data, scalar through 176-bit elements, ascending/descending declarations, nonzero/negative indices, explicit reverse ranges, sparse addresses and repeat loads. | Paired value/XZ storage is updated through typed references. The initial scope is a whole fixed one-dimensional packed integral vector memory. Automatic, aliased, class-member, port and forceable memories, other element shapes and addresses wider than 64 bits are rejected. |
| Behavioral arithmetic model | `t_fourstate_mac_model` simulates signed 18-by-27-to-48 multiply/add/shift, enable, synchronous reset and delayed global reset. | This independently written model does not certify DSP48E2 parameter modes, cascades, control words, timing checks or the vendor `glbl` implementation. |
| Supply nets | `t_fourstate_supplies` simulates constant `supply0` and `supply1` vectors. | Constants do not validate drive strengths, pullups/pulldowns, `tri0`/`tri1` or bus contention. |
| Complex assignment and ports | The inherited complex-assignment and complex-pin tests execute X/Z checks and receiver side-effect assertions. Streaming assignments use a positive runtime test. | General multi-driver, UDP, switch, specify and strength resolution remain limited. Continuous-driver conflict registration remains disabled. |
| Coverage and activity output | The coverage integration case executes array-input and compound-assignment assertions. The SAIF regressions compare VCD-derived T0/T1/TX/TZ residence times for every bit of their 1-to-301-bit signals and check close-time accounting, after removing a duplicate emitter. | The close operation credits residence time without manufacturing a transition. TC retains the fork's encoded-bit weighting; it is not certified as a physical power-tool transition metric. Unpacked-struct coverage is not certified. |
| Constant case items | `t_fourstate_case_const` checks ordinary case X/Z equality, dynamic reverse one-hot items and constant-item `casex`/`casez` matching, including 7/33/65/95-bit items, first-match order, nested cases and exact selector call counts. | Dynamic wildcard items remain unsupported. |
| Numeric conversion and two-state queues | `t_fourstate_real_conv` checks signed known integers, positive unknown-bit coercion, real rounding, `$rtoi`, mixed formatting and call counts. `t_fourstate_queue2` runs integral, bit, class and process queues plus a blocking semaphore schedule. | Four-state queue elements remain unsupported. These tests do not certify signed negative integers containing X/Z. |
| Integer timing expressions | `t_fourstate_delay_int` runs eight groups with known, mixed-X/Z and all-X/Z integer delays, standalone procedural delays and NBA capture. Its four-state functions execute exactly 16 times and two-state return functions exactly eight times. | Any unknown delay bit makes the delay zero. Zero delays require `--sched-zero-delay`. Blocking intra-assignment delays to split four-state variables and impure net delays are explicitly rejected. Transport/inertial overlap and general SDF semantics are not certified. |
| Implicit pull defaults and formatting | `t_fourstate_pull_default` retains undriven and known single-driver checks. `t_fourstate_pull_release` checks single-driver Z fallback, preserved X bits, independent wide captures, events and exact waveforms. Expanded hexadecimal formatting checks wide argument pointers and storage-padding exclusion for hex and decimal at 7/33/65/95 bits. | Driven-Z fallback is bounded to the local whole single-driver scope described above. Explicit pull primitives, contention and strengths remain unsupported. Reference simulators differ in letter case for partial all-X/Z hexadecimal digits; those added checks accept both cases. |

Compiler success alone is not accepted as capability evidence. These tests
simulate and check values; the selected VCD/FST regressions additionally compare
waveforms. The matrix describes specific tested behavior, not complete
SystemVerilog support. Only public minimal tests and existing public patches are
used; restricted vendor models and private RFSoC applications are not included.

The broader four-state suite is also audited. Its multi-driver VCD/FST demo
currently produces incorrect contention and wired-OR values, independently of
the passing single-driver trace regressions. The follow-up migrates stale
supported-feature failure expectations and aligns
unsupported diagnostic fixtures with independently checked baseline errors.
JSON fixtures follow their actual source initializer and the merged upstream
AST schema. Remaining demo failures prevent treating the whole suite as green or
the candidate as ready to replace the portable baseline.

## Public original AMD model probes

An additional Linux-cloud probe uses the unmodified Apache-2.0 sources from
[Xilinx/XilinxUnisimLibrary](https://github.com/Xilinx/XilinxUnisimLibrary), pinned
to `1c8e05fd1e9a79ceb8b996a0996674122eed086f`. The repository identifies this as
a Vivado **2020.1** UNISIM snapshot; individual file headers retain older model
revision labels. Each original file is checked against its Git blob and SHA256.
No private RFSoC inputs, generated customer files, vendor-model patches or new
license acceptance are used.

The original `DSP48E2` passes a limited combinational `ONE48` multiply profile
with all fourteen pipeline register parameters zero: `2*3`, signed `-1*3`, an
unknown input and startup GSR behavior. Five selected VCD samples agree with
Icarus. This does not certify DSP clock enables, pipeline resets, cascades,
all OPMODE/control words or the behavioral arithmetic regression above.
The original `glbl` passes startup GSR/PRLD/GTS, GRESTORE, JTAG-Z and implicit
PLL pull-up checks; fifteen selected VCD samples agree with the reference.

At the preserved `f32661859415977f2215b4c6b10f733a6f1699af` checkpoint,
original `RAMB18E2` and `RAMB36E2` fail compilation because their retained
INIT-file branches use `$readmemh` on a four-state unpacked memory, even when
the functional probe selects an empty INIT file. Their unchanged reference
probes run initialization, parity, write-first, unknown-address recovery and
synchronous reset checks. The preserved readmem checkpoint compiles all six
profiles but only `glbl` and the bounded DSP profile finish: both RAMs lose their
delayed initialization updates. The official two-state baseline reproduces that
NBA loss with an independent public program.

The bounded NBA candidate also repairs an inherited packed-vector change-event
defect, exposed after RAM initialization began to work. Its Linux cloud probe
then completes all six unchanged profiles: `glbl`, combinational `DSP48E2`,
`RAMB18E2` and `RAMB36E2` each with an empty or actual INIT file. Compilation,
model builds and runtime exits are zero, with one completion marker per profile.
All **92 selected VCD samples** match the independent Icarus reference: 15 for
`glbl`, five for DSP, 12 for each empty-file RAM and 24 for each actual-file RAM.
The latter include known, X, Z and parity bits. Internal memory checks distinguish
stored Z from a subsequent model output expression that converts Z to X.
Original vendor sources, public testbenches, fixtures and expectations remain
unchanged. The six-profile probe exits nonzero when any profile fails.

These original-model checks use `--timing` and keep warnings, including ignored
specify/timing constructs; they certify a functional subset rather than SDF.
No `XIL_TIMING`, `XIL_XECLIB` or `XIL_DR` macro is enabled. The portable checks
are independent minimal regressions; the original-model probe evidence is
separate and does not imply both portable platforms ran the vendor models.
A newer Vivado library or exact RFSoC device requires a verified matching source
and license. RFADC/RFDAC and transceiver wrappers in the public snapshot lack
some SIP implementations; XPM, DSP58 and RAMB36E5 are outside this snapshot.

## Resolver boundaries and pending acceptance

On the pull-stage baseline, `t_fourstate_demo` and its FST variant remain
acceptance failures.
Independent reference comparison finds incorrect wired-OR and 129-bit contention
values. Re-enabling the old resolver is insufficient: its `triand` truth table
also produced a wrong, driver-order-dependent result for X and 1.

The resolver candidate covers whole local two/three-driver `wire`, `tri`, `wor`
and `wand` nets as described above. Its broader demo VCD/FST acceptance must be
checked against the unchanged inherited goldens. Partial overlapping drives,
multiple-driver pull fallback, ports, hierarchy, strengths and delayed drivers
remain outside the implementation. Neither this matrix nor the selected
functional vendor probes certify complete SystemVerilog or vendor timing models.

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

## Continuing Icarus upstream acceptance

The official Icarus test collection is an additional continuing acceptance
source. Use the `ivtest` subtree of
[steveicarus/iverilog](https://github.com/steveicarus/iverilog); its former separate
`steveicarus/ivtest` repository is obsolete. Pin a full upstream commit, verify
the source and license, and record a complete test inventory before selecting
an applicable subset. Preserve upstream test sources, options and expected
results. Adapt the execution driver rather than rewriting tests or expectations
to produce passing results.

Compare the same frozen selection against a preserved Verilator baseline and
an exact candidate SHA. Record each compilation, model build and simulation's
actual exit code, timeout status, output and relevant waveforms. Report the
inventory total and separate counts for passed, failed, inapplicable, skipped
and unrun cases, with explicit reasons and a complete failure list. Distinguish
ordinary Verilog/SystemVerilog semantics, expected compilation failures and
Icarus-specific interfaces or tool behavior. An implementation disagreement
requires a source-grounded language-semantics investigation; Icarus output
alone is not proof of the language standard.

Expand the stable applicable selection in stages and add it to automatic
acceptance at the exact tested SHA. Keep the existing 132 selected Verilator
regressions, the frozen broader 108-case collection, all 34 public original AMD
profiles, and the native macOS ARM64/Rocky 8.10 portability gates. New collections
are additional gates and must not replace, silently filter or resize these
existing contracts. Full Icarus, SystemVerilog or SDF compatibility is not
claimed when only a bounded selection has run. Candidate branches and pull
requests remain drafts; acceptance results do not authorize merging or release.
