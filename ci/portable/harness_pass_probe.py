#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Exercise the actual harness pass emitter against competing native pipe writes."""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import time
from contextlib import ExitStack
from pathlib import Path

import run_regressions


def worker(root, mode, names, start_fd, ready_fd):
    """Write through the real harness emitter, or simulate compiler fragments."""
    spec = importlib.util.spec_from_file_location("regression_driver",
                                                  root / "test_regress/driver.py")
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    test = object.__new__(driver.VlTest)
    test.scenario = "vlt"
    if ready_fd is not None:
        os.write(ready_fd, b"r")
        os.close(ready_fd)
        if os.read(start_fd, 1) != b"s":
            raise RuntimeError("Missing native pipe start barrier")
        os.close(start_fd)
    if mode == "compiler":
        for _ in range(64):
            os.write(sys.stdout.fileno(), b"clang++ " + b"c" * 16384)
            os.write(sys.stdout.fileno(), b" compiler-tail\n")
            time.sleep(0.0001)
        return
    if mode in ("legacy", "atomic"):
        os.write(sys.stdout.fileno(), b"clang++ partial-command")
        # Flush this pending Python buffer before the new native pass write.
        sys.stdout.write(" pending-python-buffer")
    for name in names:
        test.name = "t_" + name
        if mode == "legacy":
            test.oprint("Self PASSED")
        else:
            test._emit_self_passed()  # pylint: disable=protected-access
        if mode == "pressure":
            time.sleep(0.0001)
    sys.stdout.flush()


def reap_workers(processes, starter):
    """Unblock the barrier before reaping workers on either success or error."""
    starter.close()
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        process.wait()


def probe(root, names):  # pylint: disable=too-many-locals
    """Capture real pipe writes; keep their lifetime and barriers together."""
    command = [sys.executable, str(Path(__file__).resolve()), "--root", str(root), "--worker"]
    outputs = {}
    for mode in ("legacy", "atomic"):
        result = subprocess.run([*command, mode, *names],
                                capture_output=True,
                                text=True,
                                check=True)
        outputs[mode] = result.stdout
    expected = [f"pipe_probe_{writer}_{index}" for writer in range(2) for index in range(64)]
    read_fd, write_fd = os.pipe()
    start_read, start_write = os.pipe()
    ready_read, ready_write = os.pipe()
    with ExitStack() as stack:
        reader = stack.enter_context(os.fdopen(read_fd, "rb"))
        writer = stack.enter_context(os.fdopen(write_fd, "wb", buffering=0))
        starter = stack.enter_context(os.fdopen(start_write, "wb", buffering=0))
        ready = stack.enter_context(os.fdopen(ready_read, "rb", buffering=0))
        pressure_command = [
            *command[:-1], "--start-fd",
            str(start_read), "--ready-fd",
            str(ready_write), command[-1]
        ]
        processes = []
        # Register before spawning: partial startup failures must also release
        # the barrier and reap already-started workers without blocking wait.
        stack.callback(reap_workers, processes, starter)
        for index in range(2):
            selected = [f"pipe_probe_{index}_{item}" for item in range(64)]
            # One ExitStack cleanup owns all workers and releases their shared
            # barrier before waiting, including exceptions during startup.
            # pylint: disable=consider-using-with
            processes.append(
                subprocess.Popen([*pressure_command, "pressure", *selected],
                                 stdout=writer,
                                 pass_fds=(start_read, ready_write)))
            processes.append(
                subprocess.Popen([*pressure_command, "compiler"],
                                 stdout=writer,
                                 pass_fds=(start_read, ready_write)))
            # pylint: enable=consider-using-with
        os.close(start_read)
        os.close(ready_write)
        for _ in processes:
            if ready.read(1) != b"r":
                raise RuntimeError("Native pipe worker did not become ready")
        starter.write(b"s" * len(processes))
        starter.close()
        writer.close()
        outputs["pressure"] = reader.read().decode("utf-8")
        statuses = [process.wait() for process in processes]
    if any(statuses):
        raise RuntimeError(f"Native pipe workers failed: {statuses}")
    pressure = outputs["pressure"]
    first_compiler, last_compiler = pressure.find("clang++ "), pressure.rfind(" compiler-tail")
    overlap = any(first_compiler < match.start() < last_compiler for match in re.finditer(
        r"^vlt/t_pipe_probe_\d+_\d+: Self PASSED$", pressure, re.MULTILINE))
    if not overlap:
        raise RuntimeError("Native pipe fixture did not overlap compiler and pass writes")
    return {
        "outputs": outputs,
        "pressure_expected": expected,
        "worker_returncodes": statuses,
        "compiler_pass_overlap": overlap
    }


def main():
    """Run a worker or persist a standalone native probe receipt."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--worker", choices=("legacy", "atomic", "pressure", "compiler"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--start-fd", type=int)
    parser.add_argument("--ready-fd", type=int)
    parser.add_argument("names", nargs="*")
    args = parser.parse_args()
    if args.worker:
        worker(args.root, args.worker, args.names, args.start_fd, args.ready_fd)
        return
    names = args.names or run_regressions.GROUPS["readmem"]
    result = probe(args.root, names)
    counts = {}
    for mode, output in result.pop("outputs").items():
        expected = result["pressure_expected"] if mode == "pressure" else names
        observed = re.findall(r"^vlt/(t_[A-Za-z0-9_]+): Self PASSED$", output, re.MULTILINE)
        counts[mode] = {
            "expected": len(expected),
            "observed": len(observed),
            "unique": len(set(observed)),
            "exact": run_regressions.passed_names(output, expected)
        }
        if args.output:
            args.output.mkdir(parents=True, exist_ok=True)
            (args.output / (mode + ".log")).write_text(output)
    result["counts"] = counts
    result["success"] = not counts["legacy"]["exact"] and counts["atomic"]["exact"] and counts[
        "pressure"]["exact"]
    text = json.dumps(result, indent=2) + "\n"
    if args.output:
        (args.output / "verification.json").write_text(text)
    print(text, end="")
    if not result["success"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
