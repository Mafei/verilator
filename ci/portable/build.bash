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
curl --fail --location --retry 3 --proto '=https' -o bison.tar.xz https://ftp.gnu.org/gnu/bison/bison-3.8.2.tar.xz
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
{
    git rev-parse HEAD
    printf 'BASELINE=%s\n' "${PORTABLE_BASELINE:-integrated}"
    git show -s --format='%H%n%P%n%s' HEAD
    uname -a
    "$CXX" --version
    flex --version
    bison --version
    if [[ $platform == rocky8-x86_64 ]]; then cat /etc/os-release; ldd --version; fi
} > out/provenance.txt
# Avoid optional allocator shared libraries in distributable builds.
autoconf
./configure --prefix=/opt/verilator-fourstate --disable-ccwarn --disable-tcmalloc --disable-jemalloc
make -C src -j2 opt
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
regress_status=0
python3 ci/portable/run_regressions.py fourstate integration upstream capabilities extended || regress_status=$?
if [[ ${smoke_status:-0} != 0 || $regress_status != 0 ]]; then
    echo "Cloud validation failed: smoke=${smoke_status:-0}, regress=$regress_status"
    exit 1
fi
python3 ci/portable/check_results.py
python3 - <<'PY'
import hashlib,pathlib
files=sorted(pathlib.Path('out').glob('*'))
pathlib.Path('out/SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in files if p.is_file()))
PY
