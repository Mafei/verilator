#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Record an owned native command's actual wait4 result and immutable log bytes."""
import argparse
import datetime
import hashlib
import json
import os
import signal
import sys
import time
from pathlib import Path


def utc():
    """Return an explicit UTC timestamp."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def digest(path):
    """Hash log bytes without loading compiler logs into memory."""
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1048576), b""):
            result.update(data)
    return result.hexdigest()


def atomic_json(path, value):
    """Create an immutable receipt and publish it after flushing."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def proc_identity(pid):
    """Supplement the actual child PID when Linux proc identity is available."""
    try:
        raw = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8")
        fields = raw[raw.rfind(")") + 2:].split()
        return {
            "pid": pid,
            "state": fields[0],
            "start_ticks": int(fields[19]),
            "clock_ticks_per_second": os.sysconf("SC_CLK_TCK")
        }
    except (FileNotFoundError, PermissionError, ValueError):
        return {"pid": pid, "start_ticks": None, "identity_unavailable": True}


def main():  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Launch a native process group and record its raw wait4 result."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cwd", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--min-disk-bytes", type=int, default=268435456)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command
    if command[:1] == ["--"]:
        command = command[1:]
    if not command or "/" in args.name or args.name in (".", ".."):
        parser.error("provide a nonempty command and a plain stage name")
    args.cwd = args.cwd.resolve(strict=True)
    args.out.mkdir(parents=True, exist_ok=True)
    log_path = args.out / (args.name + ".log")
    started_path = args.out / (args.name + ".started.json")
    finished_path = args.out / (args.name + ".finished.json")
    if any(path.exists() for path in (log_path, started_path, finished_path)):
        parser.error("stage paths already exist; use a new versioned stage name")

    def available():
        status = os.statvfs(args.cwd)
        return status.f_bavail * status.f_frsize

    minimum_available = available()
    if minimum_available < args.min_disk_bytes:
        parser.error("disk guard rejected the stage before launch")
    log_fd = os.open(log_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    started_utc = utc()
    started = time.monotonic()
    child_pid = os.fork()
    if child_pid == 0:
        try:
            os.setsid()
            os.chdir(args.cwd)
            os.dup2(log_fd, 1)
            os.dup2(log_fd, 2)
            if log_fd > 2:
                os.close(log_fd)
            os.execvpe(command[0], command, os.environ.copy())
        except (OSError, ValueError) as error:
            os.write(2,
                     (f"native observer exec failed: {type(error).__name__}: {error}\n").encode())
            os._exit(127)
    os.close(log_fd)
    receipt = {
        "schema": "native-process-wait4-v1",
        "observer_pid": os.getpid(),
        "pid": child_pid,
        "proc_identity": proc_identity(child_pid),
        "utc_started": started_utc,
        "cwd": str(args.cwd),
        "argv": command,
        "log": str(log_path),
        "disk_guard_bytes": args.min_disk_bytes,
        "initial_available_bytes": minimum_available,
        "timeout_seconds": args.timeout
    }
    atomic_json(started_path, receipt)
    reason = None
    termination_started = None
    kill_sent = False
    while True:
        waited, raw_status, usage = os.wait4(child_pid, os.WNOHANG)
        if waited:
            break
        now = time.monotonic()
        minimum_available = min(minimum_available, available())
        if reason is None and (now - started >= args.timeout
                               or minimum_available < args.min_disk_bytes):
            reason = "timeout" if now - started >= args.timeout else "disk_guard"
            termination_started = now
            try:
                os.killpg(child_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        if termination_started is not None and now - termination_started >= 5 and not kill_sent:
            try:
                os.killpg(child_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            kill_sent = True
        time.sleep(0.25)
    finished = dict(receipt)
    finished.update({
        "utc_finished": utc(),
        "elapsed_seconds": time.monotonic() - started,
        "wait4_pid": waited,
        "raw_wait_status": raw_status,
        "actual_exit": os.waitstatus_to_exitcode(raw_status),
        "exited_normally": os.WIFEXITED(raw_status),
        "exit_status": os.WEXITSTATUS(raw_status) if os.WIFEXITED(raw_status) else None,
        "signal": os.WTERMSIG(raw_status) if os.WIFSIGNALED(raw_status) else None,
        "termination_reason": reason,
        "kill_sent": kill_sent,
        "minimum_available_bytes": minimum_available,
        "final_available_bytes": available(),
        "log_bytes": log_path.stat().st_size,
        "log_sha256": digest(log_path),
        "rusage": {
            "user_seconds": usage.ru_utime,
            "system_seconds": usage.ru_stime,
            "max_rss_raw": usage.ru_maxrss,
            "max_rss_unit": "bytes" if sys.platform == "darwin" else "KiB"
        }
    })
    atomic_json(finished_path, finished)
    print(
        json.dumps({
            key: finished[key]
            for key in ("pid", "raw_wait_status", "actual_exit", "termination_reason", "log_bytes",
                        "log_sha256")
        }))
    actual_exit = finished["actual_exit"]
    return actual_exit if actual_exit >= 0 else 128 - actual_exit


if __name__ == "__main__":
    sys.exit(main())
