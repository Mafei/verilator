#!/usr/bin/env bash
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# Cloud-only build: do not install toolchains on a developer's machine.
set -euo pipefail
[[ ${GITHUB_ACTIONS:-} == true ]] || { echo 'Run this build in GitHub Actions'; exit 2; }
export TMPDIR=/tmp
export LC_ALL=C
unset VERILATOR_ROOT
root=$(pwd)
git config --global --add safe.directory "$root"
platform=${1:?platform}
mkdir -p out logs .ci-tools-src
exec > >(tee logs/build.log) 2>&1
if [[ $platform == rocky8-x86_64 ]]; then
    [[ $(uname -m) == x86_64 ]]
    source /etc/os-release
    [[ $ID == rocky && $VERSION_ID == 8.10 ]]
    set +u
    source /opt/rh/gcc-toolset-13/enable
    set -u
    export LDFLAGS='-static-libstdc++ -static-libgcc'
else
    [[ $(uname -s) == Darwin && $(uname -m) == arm64 ]]
    export CC=clang CXX=clang++
    # The constructor-split regression requires GNU Make >=4.1; Apple's
    # /usr/bin/make is 3.81. Use the installed GNU tool for shell and harness.
    portable_make_prefix=$(brew --prefix make)
    export MAKE="$portable_make_prefix/bin/gmake"
    export PATH="$portable_make_prefix/libexec/gnubin:$PATH"
    "$MAKE" --version
    lz4_prefix=$(brew --prefix lz4)
    export LIBRARY_PATH="$lz4_prefix/lib"
fi
python3 -m venv .ci-venv
source .ci-venv/bin/activate
python3 -m pip install --disable-pip-version-check distro
# Build the waveform comparator on the Rocky baseline; Ubuntu-built binaries
# can require a newer glibc. macOS uses the official ARM64 release archive.
if [[ -n ${PORTABLE_BASELINE:-} ]]; then
    : # Baselines do not need a trace comparator.
elif [[ $platform == rocky8-x86_64 ]]; then
    export RUSTUP_HOME="$root/.ci-rustup" CARGO_HOME="$root/.ci-cargo"
    curl --fail --location --retry 3 --proto '=https' -o .ci-tools-src/rustup-init.sh https://sh.rustup.rs
    sh .ci-tools-src/rustup-init.sh -y --profile minimal --default-toolchain 1.88.0 --no-modify-path
    export PATH="$CARGO_HOME/bin:$PATH"
    cargo install --locked --version 0.1.2 --root "$root/.ci-tools" wavetools
else
    curl --fail --location --retry 3 --proto '=https' -o .ci-tools-src/wavetools.tar.gz https://github.com/hudson-trading/wavetools/releases/download/v0.1.2/wavetools-v0.1.2-macos-arm64.tar.gz
    python3 - <<'PYHASH'
import hashlib
assert hashlib.sha256(open('.ci-tools-src/wavetools.tar.gz','rb').read()).hexdigest() == 'a468945b9646390c49c362a51edc7b54de53d0c3efaf852e3bf92098e7dd2867'
PYHASH
    mkdir -p .ci-tools/bin
    tar xzf .ci-tools-src/wavetools.tar.gz -C .ci-tools-src
    cp .ci-tools-src/wavetools-v0.1.2-macos-arm64/wavediff .ci-tools/bin/
fi
# The scanner and FlexLexer.h must be from the same GNU Flex release.
cd .ci-tools-src
# Bound a stalled primary connection; both endpoints must yield the same pinned bytes.
if curl --fail --location --retry 2 --retry-max-time 60 --connect-timeout 15 --max-time 120 \
    --proto '=https' --proto-redir '=https' -o bison.tar.xz https://ftp.gnu.org/gnu/bison/bison-3.8.2.tar.xz; then
    :
else
    bison_download_status=$?
    printf 'Bison primary download failed: exit %s; trying HTTPS mirror\n' "$bison_download_status"
    curl --fail --location --retry 2 --retry-max-time 60 --connect-timeout 15 --max-time 120 \
        --proto '=https' --proto-redir '=https' -o bison.tar.xz https://mirrors.kernel.org/gnu/bison/bison-3.8.2.tar.xz
fi
curl --fail --location --retry 3 --proto '=https' -o flex.tar.gz https://github.com/westes/flex/releases/download/v2.6.4/flex-2.6.4.tar.gz
python3 - <<'PY'
import hashlib
for path, expected in [('bison.tar.xz','9bba0214ccf7f1079c5d59210045227bcf619519840ebfa80cd3849cff5a5bf2'),('flex.tar.gz','e87aae032bf07c26f85ac0ed3250998c37621d95f8bd748b31f15b33c45ee995')]:
    assert hashlib.sha256(open(path,'rb').read()).hexdigest() == expected, path
PY
tar xf bison.tar.xz
tar xf flex.tar.gz
(cd bison-3.8.2 && ./configure --prefix="$root/.ci-tools" --disable-nls && make -j2 && make install)
# glibc 2.28 exposes reallocarray only with _GNU_SOURCE. Flex 2.6.4's
# configure detects the symbol without checking its declaration; an implicit
# int return truncates the pointer and crashes the generator on Rocky 8.
(cd flex-2.6.4 && CPPFLAGS=-D_GNU_SOURCE ./configure --prefix="$root/.ci-tools" --disable-nls && make -j2 && make install)
cd "$root"
export PATH="$root/.ci-tools/bin:$PATH"
export CPLUS_INCLUDE_PATH="$root/.ci-tools/include"
if [[ $platform == macos-arm64 ]]; then
    export CPLUS_INCLUDE_PATH="$CPLUS_INCLUDE_PATH:$lz4_prefix/include"
fi
python3 ci/portable/test_flexfix.py
python3 ci/portable/test_regression_results.py
python3 ci/portable/test_icarus_acceptance.py
python3 ci/portable/test_icarus_sweep.py
python3 ci/portable/test_lint_status.py
python3 ci/portable/test_finish_acceptance.py
python3 ci/portable/test_finish_wave_evidence.py
{
    git rev-parse HEAD
    printf 'BASELINE=%s\n' "${PORTABLE_BASELINE:-integrated}"
    git show -s --format='%H%n%P%n%s' HEAD
    uname -a
    "$CXX" --version
    flex --version
    bison --version
    make --version
    if [[ $platform == rocky8-x86_64 ]]; then cat /etc/os-release; ldd --version; fi
} > out/provenance.txt
# Avoid optional allocator shared libraries in distributable builds.
autoconf
./configure --prefix=/opt/verilator-fourstate --disable-ccwarn --disable-tcmalloc --disable-jemalloc
make -C src -j2 opt
if [[ -z ${PORTABLE_BASELINE:-} ]]; then
    # The interface-array control exercises checked STL iterators in the debug compiler.
    make -C src -j2 dbg
fi
python3 ci/portable/log_evidence.py compiler
if [[ -n ${PORTABLE_BASELINE:-} ]]; then
    export VERILATOR_ROOT="$root"
    git diff -- src/flexfix > out/baseline-source.patch
    python3 ci/portable/baseline.py "$root/bin/verilator" "$root/.baseline"
    exit 0
fi
# Release binary plus all runtime headers, generated make metadata, and examples.
make installbin installredirect installdata DESTDIR="$root/stage" \
    VL_INST_PUBLIC_SCRIPT_FILES='verilator verilator_gantt verilator_profcfunc' \
    VL_INST_PUBLIC_BIN_FILES=verilator_bin
cp LICENSE README.rst PORTABLE_BUILDS.md stage/opt/verilator-fourstate/
cp -R LICENSES stage/opt/verilator-fourstate/
cp out/provenance.txt stage/opt/verilator-fourstate/
if [[ $platform == rocky8-x86_64 ]]; then
    python3 ci/portable/check_elf.py stage/opt/verilator-fourstate/bin/verilator_bin > out/dependencies.txt
else
    file stage/opt/verilator-fourstate/bin/verilator_bin > out/dependencies.txt
    otool -L stage/opt/verilator-fourstate/bin/verilator_bin >> out/dependencies.txt
    python3 - <<'PY'
import subprocess
binary='stage/opt/verilator-fourstate/bin/verilator_bin'
assert 'arm64' in subprocess.check_output(['file',binary],text=True)
for line in subprocess.check_output(['otool','-L',binary],text=True).splitlines()[1:]:
    path=line.strip().split(' (')[0]
    assert path.startswith(('/usr/lib/','/System/Library/')), path
PY
fi
cp out/dependencies.txt stage/opt/verilator-fourstate/
tar -czf "out/verilator-fourstate-$platform.tar.gz" -C stage/opt verilator-fourstate
if [[ $platform == macos-arm64 ]]; then
    mkdir -p /tmp/verilator-relocated
    tar xzf "out/verilator-fourstate-$platform.tar.gz" -C /tmp/verilator-relocated
    smoke_status=0
    python3 ci/portable/smoke.py /tmp/verilator-relocated/verilator-fourstate/bin/verilator /tmp/portable-smoke || smoke_status=$?
fi
# The harness uses this checkout's headers and release binary.
export VERILATOR_ROOT="$root"
# Keep the original per-process CPU limits while compiling generated files separately.
export MAKEFLAGS="${MAKEFLAGS:-} VM_PARALLEL_BUILDS=1"
regress_status=0
# Preserve every baseline selection and add the independently checked SV semantic controls.
python3 ci/portable/run_regressions.py fourstate integration upstream capabilities extended followup readmem nba pull resolve amd-repair deassign finish_slice plusargs finish_propagation upstream_sync_20261010 icarus_semantics upstream_sync_20261011 strict_repairs_20261011 finish_boundary_20261011 upstream_daily_20261012 sv_controls_20261012 upstream_daily_20261013 upstream_daily_20261014 upstream_daily_20261014_followup upstream_daily_20261015 finish_coverage_20261015 upstream_sync_20261017 sv_semantics_20261026 fourstate_constructors_20261026 upstream_sync_20261026 tri_storage_20261026 optimizer_alias_20261026 upstream_late_20261026 sv_read_string_20261026 || regress_status=$?
if [[ ${smoke_status:-0} != 0 || $regress_status != 0 ]]; then
    echo "Cloud validation failed: smoke=${smoke_status:-0}, regress=$regress_status"
    exit 1
fi
python3 ci/portable/check_results.py
python3 ci/portable/log_evidence.py results
python3 ci/portable/log_evidence.py semantic-waves
python3 ci/portable/log_evidence.py finish-waves
python3 ci/portable/log_evidence.py controls-waves
python3 ci/portable/log_evidence.py sv-semantics-waves
thread_controls_status=0
ram_matrix_status=0
python3 ci/portable/run_thread_controls.py || thread_controls_status=$?
if [[ $thread_controls_status == 0 ]]; then python3 ci/portable/log_evidence.py thread-waves; fi
python3 ci/portable/ram_acceptance.py || ram_matrix_status=$?
if [[ $ram_matrix_status == 0 ]]; then python3 ci/portable/log_evidence.py ram-waves; fi
printf 'SYNC_20261013_CONTROL_EXITS threads=%s ram_matrix=%s\n' "$thread_controls_status" "$ram_matrix_status"
# Official inputs and expectations stay pinned and unchanged. All 18 execute;
# the documented 16 applicable cases have a separate gate from the groups above.
icarus_head=$(git rev-parse HEAD)
icarus_run_status=0
icarus_check_status=0
python3 ci/portable/icarus_acceptance.py run --expected-head "$icarus_head" || icarus_run_status=$?
python3 ci/portable/icarus_acceptance.py check --expected-head "$icarus_head" || icarus_check_status=$?
icarus_full18_status=0
python3 ci/portable/icarus_acceptance.py check --full18 --expected-head "$icarus_head" || icarus_full18_status=$?
# Preserve the original finish9 criterion, including case5's q=0 expectation.
# Collect every profile before propagating its strict output failure.
finish9_run_status=0
finish9_check_status=0
python3 ci/portable/finish_acceptance.py run --expected-head "$icarus_head" || finish9_run_status=$?
python3 ci/portable/finish_acceptance.py check --expected-head "$icarus_head" || finish9_check_status=$?
printf 'ORIGINAL_ACCEPTANCE_EXITS icarus18_run=%s applicable16_check=%s full18_check=%s finish9_run=%s finish9_check=%s\n' \
    "$icarus_run_status" "$icarus_check_status" "$icarus_full18_status" "$finish9_run_status" "$finish9_check_status"
python3 ci/portable/log_evidence.py results
if [[ $icarus_run_status != 0 || $icarus_check_status != 0 || $icarus_full18_status != 0 || $finish9_run_status != 0 || $finish9_check_status != 0 || $thread_controls_status != 0 || $ram_matrix_status != 0 ]]; then
    echo "Original acceptance validation failed: Icarus-run=$icarus_run_status, applicable16=$icarus_check_status, full18=$icarus_full18_status, finish9-run=$finish9_run_status, finish9-check=$finish9_check_status"
    exit 1
fi
