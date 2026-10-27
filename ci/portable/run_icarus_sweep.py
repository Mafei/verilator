#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Build pinned Icarus, audit its original defaults, and run the fixed 128 pair.

Example, after building a clean committed Verilator checkout::

  python3 ci/portable/run_icarus_sweep.py --platform macos-arm64 \
    --verilator-root "$PWD" --expected-verilator-sha "$(git rev-parse HEAD)" \
    --bzip2-prefix "$(brew --prefix bzip2)" --output out/icarus-v1

Rocky Linux 8.10 needs Python >= 3.9, Git, Perl, autoconf, bison, flex, gperf,
make, C/C++ compilers, zlib-devel and bzip2-devel. The existing Verilator
toolchain must remain selected (e.g. gcc-toolset-13). On macOS ARM64 install
autoconf, bison, flex, gperf, make, zlib and bzip2; put Homebrew bison/flex ahead
of the system tools. This script installs no packages and changes no TLS or
credential settings. Its default public Git fetch explicitly verifies TLS.

Use a NEW output directory for every invocation. All native stages use the
repository wait4 observer and retain logs even when the final gate fails. The
3850 reference scenarios include negative/compile-only/NI contracts; only 3069
are positive runtime tests. The fixed 128 pair is not a full-suite or complete
SystemVerilog certification. Unsupported and unresolved results remain failures.
"""

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

PIN = "f45ffabed3212a106f01cb362ef42c5d293f4513"
PUBLIC_SOURCE = "https://github.com/steveicarus/iverilog.git"
EXPECTED_INPUTS = {
    "core-inventory.json":
    "d90ada099b8aff78e164a2a70889b170200859cd6d8b90d084497dbb6f21d347",
    "first128-runtime-structural.json":
    "ce063b8824b930198819261c44265c5b6e6cc2d865b9221b736c511e685c7827",
    "first256-runtime-structural.json":
    "dd7422c86ae14b9846d737efcf43b88141171a84151058fc2c3eefa6e8dc681e",
    "all-tracked-ivtest-inputs.json":
    "7d4b3028bed36d0a6e0a01910be090e69dcc90df7e0f029d6fb063da8119c2a3",
}
EXPECTED_TYPES = {"normal": 3069, "CE": 711, "CO": 27, "RE": 2, "EF": 21, "NI": 20}
PROFILES = [("perl-default", ["perl", "vvp_reg.pl"]),
            ("python-default", [sys.executable, "vvp_reg.py"]),
            ("vpi-linux-default", ["perl", "vpi_reg.pl"])]


def digest(path):
    """Bind bytes without loading large compiler logs."""
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            value.update(data)
    return {"bytes": Path(path).stat().st_size, "sha256": value.hexdigest()}


def save(path, data):
    """Never silently replace prior evidence."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")


def manifest(root):
    """Bind the whole installed backend/VPI prefix, including executable modes."""
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("unexpected installed symlink: " + str(path))
        if path.is_file():
            result[str(path.relative_to(root))] = {
                **digest(path), "mode": path.stat().st_mode & 0o777
            }
    if not result:
        raise ValueError("empty installed prefix")
    return result


def read_git(root, *args):
    """Read exact Git metadata without credential use."""
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def tracked_manifest(root):
    """Hash every tracked source file and reject modifications against HEAD."""
    paths = subprocess.check_output(["git", "-C", str(root), "ls-files", "-z"]).split(b"\0")
    result = {}
    for raw in paths:
        if not raw:
            continue
        relative = os.fsdecode(raw)
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError("unexpected tracked source type: " + relative)
        result[relative] = {**digest(path), "mode": path.stat().st_mode & 0o777}
    if not result or read_git(root, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("pinned source has tracked changes")
    return result


def stage(args, records, name, command, cwd, env, timeout):
    """Preserve a real native command result, including wrapper/receipt agreement."""
    folder = args.output / "stages" / name
    folder.mkdir(parents=True)
    observer = args.scripts / "native_process.py"
    with (folder /
          "observer.stdout").open("xb") as stdout, (folder /
                                                    "observer.stderr").open("xb") as stderr:
        result = subprocess.run([
            sys.executable,
            str(observer), "--cwd",
            str(cwd), "--out",
            str(folder), "--name", "stage", "--timeout",
            str(timeout), "--min-disk-bytes",
            str(args.min_disk_bytes), "--", *map(str, command)
        ],
                                env=env,
                                stdout=stdout,
                                stderr=stderr,
                                check=False)
    path = folder / "stage.finished.json"
    record = {"name": name, "observer_exit": result.returncode, "receipt": str(path)}
    if path.is_file():
        receipt = json.loads(path.read_text())
        record.update(receipt)
        expected_exit = receipt["actual_exit"]
        if expected_exit < 0:
            expected_exit = 128 - expected_exit
        record["receipt_verified"] = (result.returncode == expected_exit
                                      and receipt["argv"] == list(map(str, command))
                                      and receipt["pid"] == receipt["wait4_pid"]
                                      and digest(receipt["log"]) == {
                                          "bytes": receipt["log_bytes"],
                                          "sha256": receipt["log_sha256"]
                                      })
    else:
        record.update(actual_exit=None, receipt_verified=False)
    records.append(record)
    return record


def succeeded(record):
    """A green wrapper alone cannot pass a stage."""
    return (record.get("receipt_verified") and record.get("actual_exit") == 0
            and record.get("termination_reason") is None)


def require(record):
    """Stop dependent setup after failure, retaining all earlier receipts."""
    if not succeeded(record):
        raise RuntimeError("native setup stage failed: " + record["name"])


def audit_reference(inventory, entrypoints):
    """Check every original result row against its original type contract."""
    rows = []
    errors = []
    counts = collections.Counter()
    for profile, record in entrypoints:
        expected = {row["test_id"]: row for row in inventory if row["profile"] == profile}
        found = {}
        text = Path(record["log"]).read_text(errors="replace") if record.get("log") else ""
        for line in text.splitlines():
            match = re.fullmatch(r"\s*(\S+): (Passed(?: - [^.]+)?\.|Not Implemented\.)", line)
            if match:
                name, status = match.groups()
                if name not in expected or name in found:
                    errors.append({"profile": profile, "duplicate_or_unexpected": name})
                found[name] = status
        for name, row in expected.items():
            typ = row["effective_type"]
            status = found.get(name)
            allowed = ({"Passed."} if typ == "normal" else {"Not Implemented."}
                       if typ == "NI" else {"Passed - EF.", "Passed - expected fail."}
                       if typ == "EF" else {f"Passed - {typ}."})
            accepted = status in allowed
            rows.append({
                "scenario_id": row["scenario_id"],
                "type": typ,
                "original_status": status,
                "original_contract_accepted": accepted,
                "Verilator_credit": False
            })
            if accepted:
                counts[typ] += 1
            else:
                errors.append({
                    "profile": profile,
                    "test_id": name,
                    "type": typ,
                    "original_status": status
                })
    passed = (not errors and len(rows) == 3850 and dict(counts) == EXPECTED_TYPES
              and all(succeeded(record) for _, record in entrypoints))
    return {
        "reference_only": True,
        "processed_contracts": len(rows),
        "accepted_types": dict(counts),
        "positive_runtime_passes": counts["normal"],
        "NI_not_executed": counts["NI"],
        "not_a_3850_positive_simulation_pass_claim": True,
        "errors": errors,
        "entrypoint_exits": {
            name: record.get("actual_exit")
            for name, record in entrypoints
        },
        "all_original_contracts_accepted": passed,
        "reference_gate_exit": 0 if passed else 1,
        "all_records": rows
    }


def default_slots(inventory, selected, pair):
    """Retain unselected and unfinished scenarios in the full denominator."""
    completed = {}
    for path in sorted((pair / "cases").glob("*/result.json")):
        result = json.loads(path.read_text())
        sid = result["scenario_id"]
        if sid not in selected or sid in completed:
            raise ValueError("duplicate or unselected paired result: " + sid)
        completed[sid] = {
            "pair_status": result["pair_status"],
            "result": str(path),
            **digest(path)
        }
    return [{
        "scenario_id": row["scenario_id"],
        "selected": row["scenario_id"] in selected,
        **completed.get(row["scenario_id"], {"pair_status": "UNRUN"})
    } for row in inventory]


def run(args, records, summary):  # pylint: disable=too-many-locals,too-many-statements
    """Execute dependencies, full original reference, then the paired selection."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", GIT_TERMINAL_PROMPT="0")
    # This environment variable overrides Git's explicit sslVerify setting.
    env.pop("GIT_SSL_NO_VERIFY", None)
    env["VERILATOR_ROOT"] = str(args.verilator_root)
    if args.bzip2_prefix:
        env["CPPFLAGS"] = "-I" + str(args.bzip2_prefix / "include") + " " + env.get("CPPFLAGS", "")
        env["LDFLAGS"] = ("-L" + str(args.bzip2_prefix / "lib") + " " + env.get("LDFLAGS", ""))
    for name in ("git", "perl", "autoconf", "bison", "flex", "gperf", args.make):
        if not shutil.which(name, path=env["PATH"]):
            raise ValueError("missing build dependency: " + name)
    for name in ("native_process.py", "icarus_inventory.py", "icarus_sweep.py"):
        if not (args.scripts / name).is_file():
            raise ValueError("missing companion script: " + name)
    summary["script_binding"] = {
        name: digest(args.scripts / name)
        for name in ("native_process.py", "icarus_inventory.py", "icarus_sweep.py",
                     Path(__file__).name)
    }
    head = read_git(args.verilator_root, "rev-parse", "HEAD")
    if head != args.expected_verilator_sha:
        raise ValueError("unexpected Verilator HEAD: " + head)
    if read_git(args.verilator_root, "status", "--porcelain", "--untracked-files=all", "--", "src",
                "include", "bin"):
        raise ValueError("Verilator compiler/runtime paths are not clean")
    summary["verilator_head"] = head
    source = args.output / "source"
    source.mkdir()
    require(stage(args, records, "source-init", ["git", "init", str(source)], args.output, env,
                  30))
    fetch_source = str(args.icarus_source) if args.icarus_source else PUBLIC_SOURCE
    require(
        stage(args, records, "source-fetch", [
            "git", "-c", "http.sslVerify=true", "-c", "credential.helper=", "-C",
            str(source), "fetch", "--no-tags", "--depth=1", fetch_source, PIN
        ], args.output, env, 300))
    require(
        stage(args, records, "source-checkout",
              ["git", "-C", str(source), "checkout", "--detach", PIN], args.output, env, 30))
    if read_git(source, "rev-parse", "HEAD") != PIN:
        raise ValueError("Icarus pin mismatch")
    source_before = tracked_manifest(source)
    save(args.output / "source-before.json", source_before)
    generated = args.output / "inventory"
    require(
        stage(args, records, "inventory", [
            sys.executable, args.scripts / "icarus_inventory.py", "--repo", source, "--out",
            generated
        ], source, env, 120))
    bindings = {name: digest(generated / name) for name in EXPECTED_INPUTS}
    if any(bindings[name]["sha256"] != expected for name, expected in EXPECTED_INPUTS.items()):
        raise ValueError("regenerated original inventory or fixed 128 hash mismatch")
    inventory = json.loads((generated / "core-inventory.json").read_text())
    selection = json.loads(
        (generated / "first128-runtime-structural.json").read_text())["scenario_ids"]
    selected = set(selection)
    if (len(inventory) != 3850 or len({row["scenario_id"]
                                       for row in inventory}) != 3850 or len(selection) != 128
            or len(selected) != 128):
        raise ValueError("default or selection cardinality mismatch")
    summary["input_binding"] = bindings
    summary["inventory_verified"] = True
    save(args.output / "all-default-slots-before.json",
         default_slots(inventory, selected, args.output / "pair"))
    prefix = args.output / "prefix"
    require(stage(args, records, "autoconf", ["sh", "autoconf.sh"], source, env, 120))
    require(
        stage(args, records, "configure", [source / "configure", "--prefix=" + str(prefix)],
              source, env, args.build_timeout))
    if not re.search(r"^\s*#\s*define\s+HAVE_LIBBZ2\s+1\b",
                     (source / "config.h").read_text(), re.M):
        raise ValueError("libbzip2/LXT was not enabled; install bzip2-devel or set --bzip2-prefix")
    summary["libbzip2_enabled"] = True
    require(
        stage(args, records, "make", [args.make, "-j" + str(args.jobs)], source, env,
              args.build_timeout))
    require(
        stage(args, records, "install", [args.make, "install"], source, env, args.build_timeout))
    source_built = tracked_manifest(source)
    if source_before != source_built:
        raise ValueError("build modified a tracked pinned source input")
    prefix_before = manifest(prefix)
    save(args.output / "prefix-before.json", prefix_before)
    env["PATH"] = str(prefix / "bin") + os.pathsep + env["PATH"]
    for name in ("iverilog", "vvp"):
        require(
            stage(args, records, name + "-version", [prefix / "bin" / name, "-V"], source, env,
                  30))
    fixture = args.output / "reference" / "ivtest"
    fixture.mkdir(parents=True)
    originals = json.loads((generated / "all-tracked-ivtest-inputs.json").read_text())
    for row in originals:
        original = source / row["path"]
        if digest(original)["sha256"] != row["sha256"]:
            raise ValueError("original fixture input mismatch: " + row["path"])
        target = fixture / row["path"].removeprefix("ivtest/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, target)
    shutil.copy2(source / "COPYING", args.output / "reference" / "ICARUS_COPYING")
    # The original VPI parser uses 'other' on both Linux and macOS; the frozen
    # inventory profile name vpi-linux-default denotes this unchanged contract.
    entrypoints = [(name, stage(args, records, name, command, fixture, env, args.suite_timeout))
                   for name, command in PROFILES]
    reference = audit_reference(inventory, entrypoints)
    save(args.output / "reference" / "REFERENCE_AUDIT.json", reference)
    summary["reference_gate_exit"] = reference["reference_gate_exit"]
    summary["reference_accepted_types"] = reference["accepted_types"]
    summary["reference_positive_runtime_passes"] = reference["positive_runtime_passes"]
    # Run the pair even after a reference failure: keep both real gate results.
    pair = args.output / "pair"
    paired = stage(args, records, "paired-128", [
        sys.executable, args.scripts / "icarus_sweep.py", "--pinned-repo", source, "--inventory",
        generated / "core-inventory.json", "--select",
        generated / "first128-runtime-structural.json", "--iverilog-prefix", prefix,
        "--verilator-root", args.verilator_root, "--output", pair, "--timeout",
        str(args.timeout), "--min-disk-bytes",
        str(args.min_disk_bytes), "--make", args.make
    ], args.verilator_root, env, args.pair_timeout)
    summary["pair_native_exit"] = paired.get("actual_exit")
    slots = default_slots(inventory, selected, pair)
    save(args.output / "all-default-slots-after.json", slots)
    summary["pair_status_counts"] = dict(
        collections.Counter(row["pair_status"] for row in slots if row["selected"]))
    summary["unselected_UNRUN"] = sum(not row["selected"] and row["pair_status"] == "UNRUN"
                                      for row in slots)
    result_path = pair / "results.json"
    if result_path.is_file():
        summary["pair_summary"] = json.loads(result_path.read_text())["summary"]
    source_after = tracked_manifest(source)
    prefix_after = manifest(prefix)
    save(args.output / "source-after.json", source_after)
    save(args.output / "prefix-after.json", prefix_after)
    unchanged = source_before == source_after and prefix_before == prefix_after
    summary["protected_source_and_prefix_unchanged"] = unchanged
    summary["pair_gate_exit"] = 0 if (succeeded(paired) and summary.get(
        "pair_summary", {}).get("batch_gate_exit") == 0 and summary["pair_status_counts"] == {
            "PASS_BOTH": 128
        } and summary["unselected_UNRUN"] == 3722) else 1
    summary["overall_exit"] = 0 if (unchanged and summary["reference_gate_exit"] == 0
                                    and summary["pair_gate_exit"] == 0) else 1


def final_protection(args, summary):
    """Try protection checks even when a dependency or paired stage failed."""
    audit = {}
    for label, root, collect in (("source", args.output / "source", tracked_manifest),
                                 ("prefix", args.output / "prefix", manifest)):
        before = args.output / (label + "-before.json")
        if not before.is_file():
            audit[label] = {"before_binding_available": False}
            continue
        try:
            current = collect(root)
            path = args.output / (label + "-final.json")
            save(path, current)
            audit[label] = {
                "before_binding_available": True,
                "files": len(current),
                "unchanged": current == json.loads(before.read_text()),
                "final_manifest": str(path),
                **digest(path)
            }
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            audit[label] = {
                "before_binding_available": True,
                "error": str(error),
                "unchanged": False
            }
    if any(row.get("unchanged") is False for row in audit.values()):
        summary["overall_exit"] = 1
    save(args.output / "SOURCE_PREFIX_FINAL_AUDIT.json", audit)
    summary["final_protection_audit"] = audit


def main():
    """Validate the requested platform and publish one immutable final summary."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--platform", required=True, choices=("macos-arm64", "rocky8-x86_64"))
    parser.add_argument("--verilator-root", required=True, type=Path)
    parser.add_argument("--expected-verilator-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--icarus-source",
                        type=Path,
                        help="optional existing exact-pin public checkout")
    parser.add_argument("--bzip2-prefix", type=Path)
    parser.add_argument("--make", default="gmake" if sys.platform == "darwin" else "make")
    parser.add_argument("--jobs", type=int, default=1)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--suite-timeout", type=float, default=3600)
    parser.add_argument("--build-timeout", type=float, default=3600)
    parser.add_argument("--pair-timeout", type=float, default=7200)
    parser.add_argument("--min-disk-bytes", type=int, default=4294967296)
    args = parser.parse_args()
    if sys.version_info < (3, 9):
        parser.error("Python >= 3.9 is required")
    if not re.fullmatch(r"[0-9a-f]{40}", args.expected_verilator_sha):
        parser.error("--expected-verilator-sha must be the complete committed SHA")
    if args.jobs < 1 or any(
            getattr(args, name) <= 0
            for name in ("timeout", "suite_timeout", "build_timeout", "pair_timeout")):
        parser.error("jobs and timeouts must be positive")
    machine = platform.machine().lower()
    if args.platform == "macos-arm64" and (sys.platform != "darwin" or machine != "arm64"):
        parser.error("macos-arm64 requires an actual ARM64 macOS runner")
    if args.platform == "rocky8-x86_64":
        release = Path("/etc/os-release").read_text() if Path("/etc/os-release").exists() else ""
        if (sys.platform != "linux" or machine != "x86_64"
                or not re.search(r'^ID=[\"\']?rocky[\"\']?$', release, re.M)
                or not re.search(r'^VERSION_ID=[\"\']?8\.10[\"\']?$', release, re.M)):
            parser.error("rocky8-x86_64 requires an actual Rocky Linux 8.10 x86_64 runner")
        if os.confstr("CS_GNU_LIBC_VERSION") != "glibc 2.28":
            parser.error("rocky8-x86_64 requires the actual glibc 2.28 runtime")
    args.scripts = Path(__file__).resolve().parent
    args.verilator_root = args.verilator_root.resolve(strict=True)
    args.output = args.output.resolve()
    if args.icarus_source:
        args.icarus_source = args.icarus_source.resolve(strict=True)
        if read_git(args.icarus_source, "rev-parse", "HEAD") != PIN:
            parser.error("--icarus-source must name the exact pinned checkout")
    if args.bzip2_prefix:
        args.bzip2_prefix = args.bzip2_prefix.resolve(strict=True)
    args.output.mkdir(parents=True, exist_ok=False)
    records = []
    summary = {
        "schema": "pinned-icarus-cross-platform-v1",
        "platform": args.platform,
        "actual_platform": platform.platform(),
        "libc": platform.libc_ver(),
        "machine": machine,
        "python": sys.version,
        "pin": PIN,
        "default_denominator": 3850,
        "fixed_selected": 128,
        "reference_expected_types": EXPECTED_TYPES,
        "full_suite_complete": False,
        "overall_exit": 1,
        "reference_gate_exit": None,
        "pair_gate_exit": None,
        "positive_runtime_reference_tests": 3069,
        "scope": "original reference defaults plus fixed 128 paired cases; no full SV claim",
    }
    try:
        run(args, records, summary)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        summary["blocked_or_failed"] = str(error)
    finally:
        final_protection(args, summary)
        summary["native_stages"] = records
        save(args.output / "RUN_SUMMARY.json", summary)
    print(
        json.dumps({
            key: value
            for key, value in summary.items() if key != "native_stages"
        },
                   indent=2,
                   sort_keys=True))
    return summary["overall_exit"]


if __name__ == "__main__":
    sys.exit(main())
