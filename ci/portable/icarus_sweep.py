#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run a frozen Icarus default-inventory batch with original runtime oracles.

Only normal selfchecking Perl/Python contracts have an adapter. Other scenarios
remain explicit UNRUN slots in the complete default denominator. Icarus is a
reference implementation, not a replacement for independent language semantics.
"""

import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys

PIN = "f45ffabed3212a106f01cb362ef42c5d293f4513"
DENOMINATOR = 3850
HERE = Path(__file__).resolve().parent
LANGUAGES = {
    "1995": "1364-1995",
    "2001": "1364-2001",
    "2001-noconfig": "1364-2001-noconfig",
    "2005": "1364-2005",
    "2005-sv": "1800-2005",
    "2009": "1800-2009",
    "2012": "1800-2012",
    "2017": "1800-2017",
    "2023": "1800-2023",
}
# These guards supplement the unchanged original oracle. Source excerpts printed
# by compiler warnings are not executions of their embedded FAILED selfchecks.
TOOL_FAILURE = re.compile(r"(?im)^(?:%Error(?:-|:)|%Fatal:|Internal Error:|"
                          r"Segmentation fault|Assertion .* failed).*$")
MODEL_FAILURE = re.compile(r"(?im)^.*(?:\bFAILED\b|%Error(?:-|:)|%Fatal:|Internal Error:|"
                           r"Segmentation fault|Assertion .* failed).*$")


def sha256(path):
    """Hash actual file bytes."""
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest()


def save(path, value):
    """Create a new immutable evidence file."""
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")


def git(root, *arguments):
    """Read Git metadata without modifying the repository."""
    return subprocess.check_output(["git", "-C", str(root), *arguments], text=True).strip()


def tracked_manifest(root, paths):
    """Require every protected source to match its committed Git blob."""
    entries = subprocess.check_output(
        ["git", "-C", str(root), "ls-tree", "-rz", "HEAD", "--", *paths]).split(b"\0")
    result = {}
    for raw in entries:
        if not raw:
            continue
        identity, name = raw.split(b"\t", 1)
        mode, kind, blob = identity.decode().split()
        name = os.fsdecode(name)
        path = root / name
        if kind != "blob" or path.is_symlink() or not path.is_file():
            raise ValueError("protected input must be a regular tracked file: " + name)
        data = path.read_bytes()
        if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != blob:
            raise ValueError("protected input differs from HEAD: " + name)
        result[name] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "git_mode": mode,
            "git_blob_sha1": blob
        }
    if not result:
        raise ValueError("empty protected input manifest")
    return result


def directory_manifest(root):
    """Bind installed backend modules and generated runtime headers too."""
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("unexpected protected symlink: " + str(path))
        if path.is_file():
            result[str(path.relative_to(root))] = {
                "bytes": path.stat().st_size,
                "sha256": sha256(path)
            }
    if not result:
        raise ValueError("empty protected tool directory")
    return result


def copy_fixture(repo, manifest, folder):
    """Give each engine an independent copy preserving executable helper modes."""
    folder.mkdir()
    for name in manifest:
        if name.startswith("ivtest/"):
            target = folder / name.removeprefix("ivtest/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo / name, target)
    for name in ("work", "log"):
        (folder / name).mkdir(exist_ok=True)


def stage(folder, name, command, cwd, timeout, environment, minimum):
    """Run the shared wait4 observer and verify its persisted receipt and log."""
    command = [str(item) for item in command]
    if any((folder / (name + suffix)).exists()
           for suffix in (".log", ".started.json", ".finished.json", ".observer.stdout",
                          ".observer.stderr", ".stdout", ".stderr", ".output.log")):
        raise ValueError("stage already exists; choose a new evidence directory")
    stdout = folder / (name + ".stdout")
    stderr = folder / (name + ".stderr")
    # The shell exec preserves the observer's child PID while keeping the actual
    # tool's streams separate. Python's original oracle checks stdout only.
    launcher = [
        "bash", "-c", 'task_stdout=$1; task_stderr=$2; shift 2; '
        'exec "$@" >"$task_stdout" 2>"$task_stderr"', "native-streams",
        str(stdout),
        str(stderr), *command
    ]
    observed = subprocess.run([
        sys.executable,
        str(HERE / "native_process.py"), "--cwd",
        str(cwd), "--out",
        str(folder), "--name", name, "--timeout",
        str(timeout), "--min-disk-bytes",
        str(minimum), "--", *launcher
    ],
                              env=environment,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              check=False)
    (folder / (name + ".observer.stdout")).write_bytes(observed.stdout)
    (folder / (name + ".observer.stderr")).write_bytes(observed.stderr)
    path = folder / (name + ".finished.json")
    if not path.exists():
        return {
            "status": "INFRASTRUCTURE_ERROR",
            "observer_exit": observed.returncode,
            "missing_finished_receipt": True,
            "argv": command
        }
    record = json.loads(path.read_text(encoding="utf-8"))
    log = Path(record["log"])
    if (record["argv"] != launcher or type(record["actual_exit"]) is not int  # pylint: disable=unidiomatic-typecheck
            or log.stat().st_size != record["log_bytes"] or sha256(log) != record["log_sha256"]):
        raise ValueError("native command/receipt/log binding mismatch")
    expected = (record["actual_exit"] if record["actual_exit"] >= 0 else 128 -
                record["actual_exit"])
    if observed.returncode != expected:
        raise ValueError("observer failed to propagate the actual child exit")
    record["observer_exit"] = observed.returncode
    record["invoked_argv"] = command
    for label, path in (("stdout", stdout), ("stderr", stderr)):
        if not path.is_file():
            record["status"] = "INFRASTRUCTURE_ERROR"
            record["missing_stream"] = label
            return record
        record[label] = str(path)
        record[label + "_bytes"] = path.stat().st_size
        record[label + "_sha256"] = sha256(path)
    output = folder / (name + ".output.log")
    with output.open("xb") as stream:
        stream.write(stdout.read_bytes() + stderr.read_bytes())
    record["output_log"] = str(output)
    record["output_log_sha256"] = sha256(output)
    guard = TOOL_FAILURE if name in ("compile", "build", "version") else MODEL_FAILURE
    record["failure_guard_lines"] = guard.findall(
        output.read_text(encoding="utf-8", errors="replace"))
    return record


def stage_status(record, failure):
    """Never let a success word override an error, signal, timeout or guard."""
    if record.get("missing_finished_receipt") or record.get("missing_stream"):
        return "INFRASTRUCTURE_ERROR"
    if record["termination_reason"]:
        return "TIMEOUT" if record["termination_reason"] == "timeout" else "RESOURCE_ABORT"
    if record["actual_exit"] in (126, 127):
        return "INFRASTRUCTURE_ERROR"
    if record["actual_exit"] != 0:
        return failure
    return "FAILURE_GUARD" if record["failure_guard_lines"] else None


def unsupported_only(record):
    """Reject mixed ordinary errors, internal faults and signals from this class."""
    if (record.get("actual_exit") != 1 or not record.get("exited_normally")
            or record.get("missing_stream") or record.get("missing_finished_receipt")):
        return False
    text = Path(record["output_log"]).read_text(encoding="utf-8", errors="replace")
    headers = re.findall(r"(?m)^%Error(?:-[A-Z0-9_]+)?:.*$", text)
    primary = [line for line in headers if not line.startswith("%Error: Exiting")]
    return (bool(primary) and all(line.startswith("%Error-UNSUPPORTED:") for line in primary)
            and not re.search(
                r"Internal Error:|internal fault|%Fatal:|Segmentation fault|\bFAILED\b", text))


def adapter(row):
    """Translate each supported flag explicitly; preserve every unknown flag."""
    reasons = []
    if row["family"] not in ("perl-vvp", "python-vvp"):
        reasons.append("family adapter not implemented")
    if row["effective_type"] != "normal":
        reasons.append("negative/compile-only/expected-fail contract not implemented")
    if row["gold_mode"] != "selfchecking_passed_line":
        reasons.append("gold/diff/combined-diagnostics contract not implemented")
    if not row.get("source", {}).get("exists"):
        reasons.append("primary source unavailable")
    fields = row.get("parser_fields") or {}
    raw = list(row.get("iverilog_args", []))
    if row["family"] == "perl-vvp":
        raw.insert(0, "-D__ICARUS_UNSIZED__")
        top = fields.get("testmod") or ""
        runtime = shlex.split(fields.get("plargs") or "")
        before = []
    else:
        top = fields.get("modulename") or ""
        runtime = list(fields.get("vvp_args_extended") or [])
        before = list(fields.get("vvp_args") or [])
    translated = ["--default-language", "1364-2005"]
    ledger = []
    index = 0
    while index < len(raw):
        flag = raw[index]
        consumed = [flag]
        mapped = None
        if flag.startswith("-g") and flag[2:] in LANGUAGES:
            mapped = ["--default-language", LANGUAGES[flag[2:]]]
        elif flag.startswith(("-D", "-I")) and len(flag) > 2:
            mapped = [flag]
        elif flag in ("-D", "-I", "-s") and index + 1 < len(raw):
            index += 1
            consumed.append(raw[index])
            mapped = ["--top-module" if flag == "-s" else flag, raw[index]]
        elif flag.endswith((".v", ".sv")) and not flag.startswith("-"):
            mapped = [flag]
        if mapped is None:
            reasons.append("unmapped original argument: " + flag)
        else:
            translated.extend(mapped)
        ledger.append({
            "icarus": consumed,
            "verilator": mapped,
            "status": "mapped" if mapped is not None else "ADAPTER_UNIMPLEMENTED"
        })
        index += 1
    if top:
        translated += ["--top-module", top]
    if before:
        reasons.append("vvp-before-output arguments require an explicit adapter")
    return {
        "status": "ADAPTER_UNIMPLEMENTED" if reasons else "READY",
        "reasons": reasons,
        "original_iverilog_args": raw,
        "verilator_args": translated,
        "runtime_args": runtime,
        "vvp_before": before,
        "top": top,
        "translation_ledger": ledger,
        "original_output": "vsim" if row["family"] == "perl-vvp" else "work/a.out"
    }


def run_oracle(folder, scratch, row, executed, args, environment, compiled=None):
    """Invoke the unchanged upstream oracle rather than approximating its regex."""
    if row["family"] == "perl-vvp":
        log = Path(executed["output_log"])
        if compiled is not None:
            # The original Perl selfcheck scans compiler plus runtime output.
            # Its no-gold oracle is independent of ordering between the streams.
            log = folder / "original-oracle-input.log"
            with log.open("xb") as stream:
                stream.write(Path(compiled["output_log"]).read_bytes())
                stream.write(Path(executed["output_log"]).read_bytes())
        command = [
            "perl", "-Iperl-lib", "-MDiff", "-e", 'exit(Diff::diff("", $ARGV[0], 0, 0));',
            str(log)
        ]
    else:
        log = Path(executed["stdout"])
        program = ("import json,sys,run_ivl; "
                   "options=json.loads(sys.argv[1]); "
                   "output=open(sys.argv[2],encoding='ascii').read(); "
                   "result=run_ivl.check_run_outputs(options,output,[],False); "
                   "print(json.dumps(result)); sys.exit(result[0])")
        command = [sys.executable, "-c", program, json.dumps(row["parser_fields"]), str(log)]
    return stage(folder, "oracle", command, scratch, args.timeout, environment,
                 args.min_disk_bytes)


def run_engine(engine, row, contract, args, manifest, case):  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Compile, build, execute and check one isolated original test contract."""
    folder = case / engine
    folder.mkdir()
    result = {
        "engine": engine,
        "status": "UNRUN",
        "stages": {},
        "runtime_executed": False,
        "original_oracle_accepted": None
    }
    if contract["status"] != "READY":
        result["status"] = "ADAPTER_UNIMPLEMENTED"
        return result
    scratch = folder / "scratch"
    copy_fixture(args.pinned_repo, manifest, scratch)
    environment = dict(os.environ,
                       PYTHONDONTWRITEBYTECODE="1",
                       VERILATOR_ROOT=str(args.verilator_root),
                       PATH=str(args.iverilog_prefix / "bin") + os.pathsep + os.environ["PATH"])
    source = row["source"]["path"].removeprefix("ivtest/")
    try:
        if engine == "icarus":
            command = [
                args.iverilog_prefix / "bin/iverilog", "-o", contract["original_output"],
                *contract["original_iverilog_args"]
            ]
            if contract["top"]:
                command += ["-s", contract["top"]]
            command.append(source)
        else:
            command = [
                args.verilator_root / "bin/verilator", "--cc", "--exe", "--main", "--assert",
                "--timing", "--fourstate", "--no-skip-identical", "-Wno-fatal", "--Mdir", "obj",
                "--prefix", "Vt", *contract["verilator_args"], source
            ]
        compiled = stage(folder, "compile", command, scratch, args.timeout, environment,
                         args.min_disk_bytes)
        result["stages"]["compile"] = compiled
        status = stage_status(compiled, "COMPILE_FAILED")
        if status:
            if engine == "verilator" and unsupported_only(compiled):
                status = "UNSUPPORTED_DIAGNOSTIC"
            result["status"] = status
            return result
        if engine == "verilator":
            built = stage(folder, "build", [args.make, "-C", "obj", "-f", "Vt.mk", "-j1"], scratch,
                          args.timeout, environment, args.min_disk_bytes)
            result["stages"]["build"] = built
            status = stage_status(built, "BUILD_FAILED")
            if status:
                result["status"] = status
                return result
            command = [scratch / "obj/Vt", "+verilator+quiet", *contract["runtime_args"]]
        else:
            command = [
                args.iverilog_prefix / "bin/vvp", *contract["vvp_before"],
                contract["original_output"], *contract["runtime_args"]
            ]
        executed = stage(folder, "run", command, scratch, args.timeout, environment,
                         args.min_disk_bytes)
        result["stages"]["run"] = executed
        result["runtime_executed"] = ("actual_exit" in executed
                                      and executed["actual_exit"] not in (126, 127)
                                      and not executed.get("missing_stream"))
        status = stage_status(executed, "RUNTIME_FAILED")
        if "actual_exit" in executed and not executed["termination_reason"]:
            checked = run_oracle(folder, scratch, row, executed, args, environment, compiled)
            result["stages"]["oracle"] = checked
            result["original_oracle_accepted"] = (checked.get("actual_exit") == 0
                                                  and checked.get("termination_reason") is None)
            status = status or stage_status(checked, "ORACLE_FAILED")
        result["status"] = status or "PASS"
        return result
    finally:
        mutated = []
        for name, expected in manifest.items():
            if name.startswith("ivtest/"):
                path = scratch / name.removeprefix("ivtest/")
                if not path.is_file() or path.is_symlink() or sha256(path) != expected["sha256"]:
                    mutated.append(name)
        result["private_fixture_input_mutations"] = mutated
        if mutated:
            result["status"] = "INPUT_MUTATED"
        products = {}
        for path in sorted(scratch.rglob("*")):
            name = str(path.relative_to(scratch))
            if (not path.is_file() or path.is_symlink() or "ivtest/" + name in manifest
                    or path.suffix in (".o", ".gch") or name == contract["original_output"]
                    or (name.startswith("obj/") and path.suffix not in (".vcd", ".fst"))):
                continue
            target = folder / "products" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            products[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}
        result["retained_products"] = products
        if result["status"] == "PASS" and not args.keep_scratch:
            shutil.rmtree(scratch)
            result["scratch_removed"] = True
        else:
            result["scratch_removed"] = False


def pair_status(reference, verilator):
    """Separate unreviewed differences from an established reference bug."""
    if reference["status"] == verilator["status"] == "ADAPTER_UNIMPLEMENTED":
        return "ADAPTER_UNIMPLEMENTED"
    if reference["status"] != "PASS":
        return "REFERENCE_" + reference["status"]
    if verilator["status"] == "PASS":
        return "PASS_BOTH"
    if verilator["status"] in ("ORACLE_FAILED", "FAILURE_GUARD"):
        return ("UNREVIEWED_OUTPUT_DIFFERENCE"
                if verilator["runtime_executed"] else "VERILATOR_TOOL_DIAGNOSTIC_GUARD")
    return "VERILATOR_" + verilator["status"]


def summarize(rows, selected):
    """Always retain the full default denominator and explicit unrun counts."""
    return {
        "full_default_denominator":
        DENOMINATOR,
        "selected":
        selected,
        "completed":
        len(rows),
        "selected_unrun":
        selected - len(rows),
        "unselected_UNRUN":
        DENOMINATOR - selected,
        "full_suite_complete":
        False,
        "pair_status_counts":
        dict(Counter(row["pair_status"] for row in rows)),
        "engine_status_counts": {
            engine: dict(Counter(row[engine]["status"] for row in rows))
            for engine in ("icarus", "verilator")
        },
        "native_stage_receipts":
        sum("actual_exit" in step for row in rows for engine in ("icarus", "verilator")
            for step in row[engine]["stages"].values())
    }


def main():  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Bind clean tools/inputs, collect every selected case, and fail unresolved gates."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pinned-repo", required=True, type=Path)
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--select", required=True, type=Path)
    parser.add_argument("--iverilog-prefix", required=True, type=Path)
    parser.add_argument("--verilator-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--min-disk-bytes", type=int, default=4294967296)
    parser.add_argument("--keep-scratch", action="store_true")
    parser.add_argument("--make", default="make")
    args = parser.parse_args()
    for name in ("pinned_repo", "inventory", "select", "iverilog_prefix", "verilator_root"):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.output = args.output.resolve()
    if git(args.pinned_repo, "rev-parse", "HEAD") != PIN:
        raise ValueError("wrong Icarus source commit")
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    if len(inventory) != DENOMINATOR or len({r["scenario_id"] for r in inventory}) != DENOMINATOR:
        raise ValueError("wrong or duplicated full default inventory")
    if Counter(row["family"] for row in inventory) != {
            "perl-vvp": 3028,
            "python-vvp": 746,
            "vpi": 76
    }:
        raise ValueError("wrong default profile denominators")
    ids = json.loads(args.select.read_text(encoding="utf-8"))["scenario_ids"]
    by_id = {row["scenario_id"]: row for row in inventory}
    if not ids or len(ids) != len(set(ids)) or any(key not in by_id for key in ids):
        raise ValueError("selection is empty, duplicated or outside the full inventory")
    selected = [by_id[key] for key in ids]
    head = git(args.verilator_root, "rev-parse", "HEAD")
    if git(args.verilator_root, "status", "--porcelain", "--", "src", "include", "bin"):
        raise ValueError("Verilator compiler/runtime inputs are dirty")
    original = tracked_manifest(args.pinned_repo, ["ivtest", "COPYING"])
    runtime = tracked_manifest(args.verilator_root, ["src", "include", "bin"])
    installed = directory_manifest(args.iverilog_prefix)
    generated_runtime = directory_manifest(args.verilator_root / "include")
    tool_paths = {
        "verilator_bin": args.verilator_root / "bin/verilator_bin",
        "verilator_driver": args.verilator_root / "bin/verilator",
        "iverilog": args.iverilog_prefix / "bin/iverilog",
        "vvp": args.iverilog_prefix / "bin/vvp",
        "runner": Path(__file__).resolve(),
        "native_observer": HERE / "native_process.py",
        "make": Path(shutil.which(args.make) or args.make).resolve()
    }
    tools = {
        name: {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256(path)
        }
        for name, path in tool_paths.items()
    }
    args.output.mkdir(parents=True, exist_ok=False)
    save(args.output / "initial-summary.json", summarize([], len(selected)))
    licenses = args.output / "licenses"
    licenses.mkdir()
    for source, target in (("COPYING", "root-COPYING"), ("ivtest/COPYING", "ivtest-COPYING")):
        shutil.copy2(args.pinned_repo / source, licenses / target)
    for name, data in (("inputs-before.json", original), ("runtime-before.json", runtime),
                       ("installed-icarus-before.json",
                        installed), ("runtime-directory-before.json", generated_runtime)):
        save(args.output / name, data)
    environment = dict(os.environ,
                       VERILATOR_ROOT=str(args.verilator_root),
                       PYTHONDONTWRITEBYTECODE="1")
    version = stage(args.output, "version", [tool_paths["verilator_driver"], "--version"],
                    args.verilator_root, args.timeout, environment, args.min_disk_bytes)
    version_text = (Path(version["stdout"]).read_text(
        encoding="utf-8") if "stdout" in version else "")
    if stage_status(version,
                    "VERSION_FAILED") or head[:9] not in version_text or "(mod)" in version_text:
        raise ValueError("compiler version does not bind the clean checked-out HEAD")
    reference_versions = {}
    for name in ("iverilog", "vvp"):
        folder = args.output / (name + "-version")
        folder.mkdir()
        record = stage(folder, "version", [tool_paths[name], "-V"], args.pinned_repo, args.timeout,
                       environment, args.min_disk_bytes)
        text = (Path(record["output_log"]).read_text(
            encoding="utf-8") if "output_log" in record else "")
        if (stage_status(record, "VERSION_FAILED") or "version 14.0" not in text
                or PIN[:7] not in text):
            raise ValueError("reference version does not match the pinned Icarus source")
        reference_versions[name] = record
    binding = {
        "schema": "icarus-sweep-recovery-v2",
        "icarus_commit": PIN,
        "verilator_commit": head,
        "tools": tools,
        "version": version,
        "reference_versions": reference_versions,
        "inventory_sha256": sha256(args.inventory),
        "selection_sha256": sha256(args.select),
        "timeout_per_stage_seconds": args.timeout,
        "make_parallelism": 1,
        "new_actual_run": True,
        "no_historical_pass_credit": True
    }
    save(args.output / "binding.json", binding)
    cases = args.output / "cases"
    cases.mkdir()
    rows = []
    for index, row in enumerate(selected):
        case = cases / f"{index:04d}"
        case.mkdir()
        save(case / "original-contract.json", row)
        contract = adapter(row)
        save(case / "adapter.json", contract)
        result = {"scenario_id": row["scenario_id"], "test_id": row["test_id"]}
        for engine in ("icarus", "verilator"):
            result[engine] = run_engine(engine, row, contract, args, original, case)
        result["pair_status"] = pair_status(result["icarus"], result["verilator"])
        save(case / "result.json", result)
        rows.append(result)
        save(case / "progress-summary.json", summarize(rows, len(selected)))
        print(json.dumps({
            "completed": len(rows),
            "selected": len(selected),
            "scenario_id": row["scenario_id"],
            "pair_status": result["pair_status"]
        }),
              flush=True)
    after = tracked_manifest(args.pinned_repo, ["ivtest", "COPYING"])
    runtime_after = tracked_manifest(args.verilator_root, ["src", "include", "bin"])
    installed_after = directory_manifest(args.iverilog_prefix)
    generated_after = directory_manifest(args.verilator_root / "include")
    for name, data in (("inputs-after.json", after), ("runtime-after.json", runtime_after),
                       ("installed-icarus-after.json",
                        installed_after), ("runtime-directory-after.json", generated_after)):
        save(args.output / name, data)
    unchanged = (original == after and runtime == runtime_after and installed == installed_after
                 and generated_runtime == generated_after
                 and head == git(args.verilator_root, "rev-parse", "HEAD")
                 and PIN == git(args.pinned_repo, "rev-parse", "HEAD")
                 and all(sha256(Path(item["path"])) == item["sha256"] for item in tools.values()))
    summary = summarize(rows, len(selected))
    summary["protected_inputs_and_tools_unchanged"] = unchanged
    summary["batch_gate_exit"] = (0 if unchanged and len(rows) == len(selected)
                                  and all(row["pair_status"] == "PASS_BOTH"
                                          for row in rows) else 1)
    results = {row["scenario_id"]: row for row in rows}
    slots = [{
        "scenario_id":
        row["scenario_id"],
        "status":
        results[row["scenario_id"]]["pair_status"] if row["scenario_id"] in results else "UNRUN"
    } for row in inventory]
    save(args.output / "results.json", {
        "binding": binding,
        "summary": summary,
        "results": rows,
        "full_default_slots": slots
    })
    print(json.dumps(summary, indent=2), flush=True)
    return summary["batch_gate_exit"]


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f"Icarus sweep failed: {type(error).__name__}: {error}", file=sys.stderr)
        sys.exit(2)
