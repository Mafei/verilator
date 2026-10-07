# Experimental four-state builds

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
- Keep the dev policy disabling continuous-driver conflict resolution for
  complex assignments. Bus contention remains an experimental limitation.
- Route paired public variables through residual VPI registration rather than
  the newer value-only table; preserve X/Z comparisons in value callbacks.
- Preserve dev four-state test fixtures and feature generic JSON fixtures.
  A successful focused CI run does not certify the entire upstream regression
  suite or complete IEEE four-state semantics.

The GNU Flex signature adjustment removes OS-version guessing in `src/flexfix`.
It was previously verified in the authorized SS-OCT experiment; only this public
Verilator patch is reused, with SHA256
`799d300562094b602d559eecc18d0742f8e393a1ff96480d3d3cb8992735654b`.
No private application models or project files are included.

## Platforms and artifacts

Builds run only in GitHub Actions on pushes, pull requests, or manual dispatch.
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

Artifacts contain the optimized compiler, Python/Perl scripts, runtime headers
and sources, generated make metadata, CMake/pkg-config data, examples, licenses,
provenance, dependency reports, and checksums. Debug/coverage executables are
not included. Unpack anywhere and invoke `bin/verilator`; leave `VERILATOR_ROOT`
unset to use the relocated installation's own runtime files.

CI checks the relocated package by compiling and executing a four-state timing
model, including a required failure on an unknown comparison. The Linux package
is tested in a new Rocky 8.10 container with a different installation path.
Published artifacts are development snapshots, not releases.

The manual `Original four-state baselines` workflow builds both original commits
with the same Rocky toolchain and runs a common scalar and aggregate probe.
Only the public test harness and GNU Flex header adjustment are copied into
these checkouts. Results and the exact source adjustment are uploaded as evidence.
