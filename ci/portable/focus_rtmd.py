#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run independent RTMD and synchronization checks without replacing original acceptance."""
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from run_regressions import actual_passed_names, parse_summary
from trace_focus_audit import audit_original

SOLVER_CASES = ('std_randomize_unq_arr', 'constraint_solve_before', 'constraint_unsat')
CASES = ('rtmd_dump', 'trace_all_formats', 'rtmd_fourstate_storage', 'fourstate_trace_vcd',
         'fourstate_trace_fst', 'fourstate_trace_saif', 'fourstate_trace_resume',
         'fourstate_rtmd_trace', 'fourstate_rtmd_trace_fst', 'fourstate_rtmd_trace_saif',
         *SOLVER_CASES, 'constraint_solve_before_array', 'unconnected', 'unconnected_drive_bad',
         'unconnected_pull_bits', 'unconnected_pull_bits_fourstate', 'cover_toggle_width',
         'cover_line_cc', 'cover_line_only', 'property_nfa_edge_perf', 'wait_null_trigger',
         'tristate_pkg_net', 'fourstate_saif_time')


def sha(path):
    """Identify the actual compiler, solver, log and source bytes."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():  # pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Retain every exit and distinguish missing execution evidence from a pass."""
    root = Path(__file__).resolve().parents[2]
    output = root / 'out/rtmd-focus'
    output.mkdir(parents=True, exist_ok=True)
    solver = shutil.which('z3')
    provenance = {
        'head':
        subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'run_id':
        os.environ.get('GITHUB_RUN_ID'),
        'platform':
        platform.platform(),
        'machine':
        platform.machine(),
        'compiler_sha256':
        sha(root / 'bin/verilator_bin'),
        'solver_path':
        solver,
        'solver_sha256':
        sha(Path(solver)) if solver else None,
        'solver_version':
        subprocess.check_output([solver, '--version'], text=True).strip() if solver else None,
        'pinned_icarus_supplement':
        'NOT_RUN_HERE; separate pinned step required',
        'unconnected_Z':
        'NOT_TESTED; excluded from acceptance'
    }
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')
    results = {}
    for name in CASES:
        case = output / name
        case.mkdir(exist_ok=True)
        env = os.environ.copy()
        if name in SOLVER_CASES and solver:
            pieces = [
                sys.executable,
                str(root / 'ci/portable/solver_probe.py'),
                str(case / 'solver'), solver, '-in'
            ]
            if any(any(c.isspace() for c in p) for p in pieces):
                raise ValueError('Solver command cannot contain whitespace in a path')
            env['VERILATOR_SOLVER'] = ' '.join(pieces)
        command = [
            sys.executable, 'driver.py', '--vlt', '-j1', '--no-skip-identical', '--obj-suffix',
            '_rtmdfocus', 't/t_' + name + '.py'
        ]
        logfile = case / 'driver.log'
        with logfile.open('w') as stream:
            try:
                child = subprocess.run(command,
                                       cwd=root / 'test_regress',
                                       env=env,
                                       stdout=stream,
                                       stderr=subprocess.STDOUT,
                                       timeout=900,
                                       check=False)
                code = child.returncode
            except subprocess.TimeoutExpired:
                code = None
        log = logfile.read_text()
        try:
            status, counts = parse_summary(log)
        except ValueError:
            status, counts = 'INVALID', {}
        names = actual_passed_names(log)
        passed = (code == 0 and status == 'PASSED' and names == [name]
                  and counts.get('passed') == 1 and not any(
                      counts.get(key, 0)
                      for key in ('failed', 'skipped', 'left', 'running', 'failed-first')))
        row = {
            'actual_exit': code,
            'status': status,
            'counts': counts,
            'passed': passed,
            'passed_names': names,
            'log_sha256': sha(logfile),
            'command': command,
            'driver_sha256': sha(root / 'test_regress/t' / ('t_' + name + '.py'))
        }
        if name in SOLVER_CASES:
            starts = list((case / 'solver').glob('*.started.json'))
            finishes = list((case / 'solver').glob('*.finished.json'))
            row['solver_started'] = len(starts)
            row['solver_finished'] = len(finishes)
            row['solver_actual_exits'] = [
                json.loads(p.read_text())['actual_exit'] for p in finishes
            ]
            row['solver_execution_verified'] = bool(
                starts and len(starts) == len(finishes)
                and all(code == 0 for code in row['solver_actual_exits']))
            row['passed'] &= row['solver_execution_verified']
        if name.startswith('cover_'):
            data = root / 'test_regress/obj_vlt' / ('t_' + name + '_rtmdfocus') / 'coverage.dat'
            row['coverage_actual_bytes_available'] = data.is_file()
            if data.is_file():
                shutil.copy2(data, case / 'coverage.dat')
                points = []
                for line in data.read_text().splitlines():
                    if line.startswith("C '"):
                        key, hits = line[3:].rsplit("' ", 1)
                        points.append({'key': key, 'hits': int(hits)})
                row['point_denominator'] = len(points)
                row['points_hit'] = sum(point['hits'] > 0 for point in points)
                row['total_hits'] = sum(point['hits'] for point in points)
                row['coverage_sha256'] = sha(data)
                (case / 'coverage-points.json').write_text(json.dumps(points, indent=2) + '\n')
        obj = root / 'test_regress/obj_vlt' / ('t_' + name + '_rtmdfocus')
        if name in ('fourstate_trace_vcd', 'fourstate_trace_fst'):
            row['independent_trace_audit'] = audit_original(root, obj, name.rsplit('_', 1)[1])
        if obj.is_dir():
            for artifact in obj.rglob('*'):
                if (artifact.is_file() and artifact.suffix
                        in ('.vcd', '.fst', '.saif', '.json', '.log', '.status')):
                    dest = case / 'actual' / artifact.relative_to(obj)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(artifact, dest)
        results[name] = row
        (output / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print('RTMD_FOCUS ' + json.dumps({'name': name, **row}), flush=True)
    return 0 if all(row['passed'] for row in results.values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
