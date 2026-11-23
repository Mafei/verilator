#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Forward the solver's standard streams unchanged and record its actual child exit."""
import datetime
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path


def main():
    """Keep the SMT protocol on stdin/stdout; write receipts only to private files."""
    directory = Path(sys.argv[1])
    command = sys.argv[2:]
    directory.mkdir(parents=True, exist_ok=True)
    name = str(uuid.uuid4())
    receipt = {
        'argv': command,
        'wrapper_pid': os.getpid(),
        'parent_pid': os.getppid(),
        'utc_started': datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    with subprocess.Popen(command) as child:
        receipt['child_pid'] = child.pid
        (directory / (name + '.started.json')).write_text(json.dumps(receipt, indent=2) + '\n')
        result = child.wait()
    receipt['actual_exit'] = result
    receipt['utc_finished'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    (directory / (name + '.finished.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    return result if result >= 0 else 128 - result


if __name__ == '__main__':
    raise SystemExit(main())
