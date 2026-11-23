#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Keep the original fixed128 run intact, then record the separate packed-pull probe."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

PIN = 'f45ffabed3212a106f01cb362ef42c5d293f4513'


def main():
    """Preserve the original exit and never classify unsupported as a runtime pass."""
    args = sys.argv[1:]
    root = Path(args[args.index('--verilator-root') + 1]).resolve()
    output = Path(args[args.index('--output') + 1]).resolve()
    original = subprocess.run(
        [sys.executable, str(root / 'ci/portable/run_icarus_sweep.py'), *args],
        check=False).returncode
    dest = root / 'out/rtmd-focus/pinned-pull'
    dest.mkdir(parents=True, exist_ok=True)
    report = {
        'original_fixed128_actual_exit': original,
        'expected_pin': PIN,
        'Z': 'NOT_TESTED',
        'status': 'NOT_RUN',
        'classification': 'Supplemental only; original inventory and acceptance unchanged'
    }
    prefix = output / 'prefix'
    source = output / 'source'
    binary = prefix / 'bin/iverilog'
    before = output / 'prefix-before.json'
    status = 1
    if binary.is_file() and before.is_file() and (source / '.git').exists():
        observed = subprocess.check_output(
            ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
        identity = hashlib.sha256(binary.read_bytes()).hexdigest()
        frozen = json.loads(before.read_text())
        expected = frozen['bin/iverilog']['sha256']
        vvp_identity = hashlib.sha256((prefix / 'bin/vvp').read_bytes()).hexdigest()
        report['vvp_sha256'] = vvp_identity
        report.update({'observed_pin': observed, 'iverilog_sha256': identity})
        if (observed != PIN or identity != expected
                or vvp_identity != frozen['bin/vvp']['sha256']):
            report['status'] = 'IDENTITY_MISMATCH_NOT_EXECUTED'
        else:
            version = subprocess.run([str(binary), '-V'], capture_output=True, check=False)
            (dest / 'version.log').write_bytes(version.stdout + version.stderr)
            fixture = root / 'test_regress/t/t_unconnected_pull_bits.v'
            report['fixture_sha256'] = hashlib.sha256(fixture.read_bytes()).hexdigest()
            command = [
                str(binary), '-g2012', '-s', 't', '-o',
                str(dest / 'model.vvp'),
                str(fixture)
            ]
            compile_result = subprocess.run(command, capture_output=True, check=False)
            log = compile_result.stdout + compile_result.stderr
            (dest / 'compile.log').write_bytes(log)
            report.update({
                'compile_argv': command,
                'compile_actual_exit': compile_result.returncode
            })
            text = log.decode(errors='replace').lower()
            unsupported = ('unconnected_drive' in text
                           and ('not supported' in text or 'sorry:' in text))
            if unsupported:
                report['status'] = 'UNSUPPORTED_NOT_EXECUTED'
            elif compile_result.returncode:
                report['status'] = 'COMPILE_FAILED'
            else:
                command = [str(prefix / 'bin/vvp'), '-n', str(dest / 'model.vvp')]
                try:
                    result = subprocess.run(command, capture_output=True, timeout=120, check=False)
                    data = result.stdout + result.stderr
                    (dest / 'runtime.log').write_bytes(data)
                    expected = [
                        f'PULL_BITS width={width} samples=4 per_bit=1 controls=1'
                        for width in (7, 33, 65, 34)
                    ]
                    lines = data.decode(errors='replace').splitlines()
                    good = result.returncode == 0 and all(
                        lines.count(line) == 1 for line in expected)
                    report.update({
                        'runtime_argv': command,
                        'runtime_actual_exit': result.returncode,
                        'status': 'PASS_PER_BIT' if good else 'RUNTIME_FAILED'
                    })
                    status = 0 if good else 1
                except subprocess.TimeoutExpired:
                    report['status'] = 'RUNTIME_TIMEOUT'
    else:
        report['reason'] = 'Pinned prefix/source or its original identity manifest is unavailable'
    (dest / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('PINNED_PULL_FOCUS ' + json.dumps(report), flush=True)
    # Failure of the original acceptance always dominates this extra observation.
    return original if original else status


if __name__ == '__main__':
    raise SystemExit(main())
