#!/usr/bin/env python3
"""CC0-1.0: Bounded termination reference/baseline runner; no compiler modifications."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess

C = Path(__file__).resolve().parent
E = Path('/workspace/evidence/fourstate-followup-20261009/finish-controls-v1')
VROOT = Path('/tmp/verilator-followup-20261009')
FROOT = Path('/tmp/verilator-icarus-lint-20261009')
BIN = VROOT / 'bin/verilator_bin'
BIN_SHA = '0dec37177ade528731050dba1d170e7bd0eed8e4882c2f7e0f6371454ca2efb0'
IV = Path('/workspace/cloud-tools/iverilog/usr/bin/iverilog')
IVL = Path('/workspace/cloud-tools/iverilog/usr/lib/x86_64-linux-gnu/ivl')
VVP = Path('/workspace/cloud-tools/iverilog/usr/bin/vvp')
PROFILE_NAMES = ['initial', 'coroutine', 'task_caller', 'function_caller', 'fork_join', 'nba_postponed', 'inactive_future', 'final_finish']
spec = importlib.util.spec_from_file_location('native_helpers', '/workspace/icarus-acceptance-20261008/run_acceptance_v2.py')
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)

def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (768 * 1024 * 1024, 768 * 1024 * 1024))
h.no_core_files = limits

def size():
    return sum(p.stat().st_size for p in C.rglob('*') if p.is_file())

def guard():
    free = os.statvfs(C).f_bavail * os.statvfs(C).f_frsize
    used = size()
    if free < 200 * 1024 * 1024 or used >= 150 * 1024 * 1024:
        raise RuntimeError(f'Resource guard: free={free}, owned={used}; no later profile launched')
    return {'free_bytes': free, 'owned_bytes': used, 'minimum_free_bytes': 200 * 1024 * 1024,
            'maximum_owned_bytes': 150 * 1024 * 1024, 'per_process_RLIMIT_AS_bytes': 768 * 1024 * 1024}

def expected(case):
    time = 0 if case == 0 else 1
    first = f'OBS {case} before {time}'
    if case == 7:
        return [[first, f'FINAL 7 A 1 q=0'], [first, f'FINAL 7 B 1 q=0']]
    return [[first, f'FINAL {case} {time} q=0']]

def check(log, case):
    raw = Path(log).read_text()
    selected = [line for line in raw.splitlines() if re.match(r'^(OBS |FINAL |UNREACHABLE)', line)]
    forbidden = [line for line in raw.splitlines() if 'UNREACHABLE' in line or re.search(r'(?i)(%Error|fatal|error:)', line)]
    return {'expected_literal_alternatives': expected(case), 'actual_owned_lines': selected,
            'forbidden_lines': forbidden, 'strict_output_passed': selected in expected(case) and not forbidden,
            'full_raw_output_sha256': h.sha(log), 'no_native_zero_equals_pass_rule': True,
            'final_order_not_assumed': case == 7,
            'NBA_final_old_value_is_scoped_ordering_inference': case == 5}

def wave(path):
    if not path.exists():
        return {'present': False, 'no_semantic_pass_inferred_from_absence': True}
    raw = path.read_text()
    declarations = re.findall(r'\$var\s+\w+\s+(\d+)\s+(\S+)\s+q\b', raw)
    codes = {c for _, c in declarations}
    changes = []
    time = 0
    for line in raw.splitlines():
        if line.startswith('#'):
            time = int(line[1:])
        m = re.fullmatch(r'([01xzXZ])(\S+)', line)
        if m and m[2] in codes:
            changes.append([time, m[1].lower()])
    return {'present': True, 'path': str(path), 'sha256': h.sha(path),
            'timescale_1ps': bool(re.search(r'\$timescale\s+1ps\s+\$end', raw)),
            'q_raw_selected_history': changes, 'precision_scope': 'physical ps; complete raw VCD retained',
            'same_region_order_not_inferred_from_VCD': True}

ap = argparse.ArgumentParser()
ap.add_argument('--phase', choices=['reference', 'baseline'], required=True)
args = ap.parse_args()
assert args.phase == 'baseline', 'v2 is baseline-only; reference-v1 stays immutable'
output = C / 'baseline-v2'
assert not output.exists()
output.mkdir()
env = os.environ.copy()
env['VERILATOR_ROOT'] = str(VROOT)
env['MAKEFLAGS'] = 'VM_PARALLEL_BUILDS=0'
assert h.sha(BIN) == BIN_SHA
assert subprocess.check_output(['git', '-C', str(FROOT), 'rev-parse', 'HEAD'], text=True).strip() == 'fdb3be1ab4241be77a428c8192ff2cfb16f18090'
assert subprocess.check_output(['git', '-C', str(VROOT), 'rev-parse', 'HEAD'], text=True).strip() == '5a73c185425d2e5e7d8a3b53549175f1d5e09400'
src = subprocess.check_output(['git', '-C', str(VROOT), 'ls-files', 'src', 'include'], text=True).splitlines()
assert len(src) == 434
assert all(h.sha(VROOT / p) == h.sha(FROOT / p) for p in src)
protected = {str(C / 'finish_controls.sv'): h.sha(C / 'finish_controls.sv'), str(Path(__file__)): h.sha(__file__),
             str(BIN): BIN_SHA, str(IV): h.sha(IV), str(VVP): h.sha(VVP)}
for root in (FROOT, VROOT):
    for p in subprocess.check_output(['git', '-C', str(root), 'ls-files'], text=True).splitlines():
        protected[str(root / p)] = h.sha(root / p)
sdk = json.loads(Path('/workspace/evidence/amd-repair-20261008/latest-62b6849-preparation-v1/identity-complete/runtime-root.json').read_text())['sha256']
assert len(sdk) == 79
for p in sdk:
    protected[str(VROOT / p)] = h.sha(VROOT / p)
for p in IVL.rglob('*'):
    if p.is_file():
        protected[str(p)] = h.sha(p)
h.save(E / ('baseline-v2-protected-before.json'), protected)
start_memory = h.cg_events()
h.save(E / ('baseline-v2-started.json'), {'created_utc': datetime.now(timezone.utc).isoformat(),
    'phase': args.phase, 'profiles_selected': 8, 'compiler_head': '5a73c185425d2e5e7d8a3b53549175f1d5e09400',
    'context_head': 'fdb3be1ab4241be77a428c8192ff2cfb16f18090', 'compiler_is_not_fresh_fdb': True,
    'compiler_sha256': BIN_SHA, 'source_434_fdb_equals_5a': True,
    'runtime': str(VROOT), 'runtime_files': 79, 'source_sha256': h.sha(C / 'finish_controls.sv'),
    'iverilog_sha256': h.sha(IV), 'vvp_sha256': h.sha(VVP), 'resource': guard(), 'memory_events_before': start_memory,
    'jobs': 1, 'VM_PARALLEL_BUILDS': 0, 'documented_finish_hook_override': False, 'warning_policy': 'only -Wno-FUTURE added; all other warnings fatal', 'preparation_v1_preserved': True})
if args.phase == 'reference':
    identity = h.stage(output, 'iverilog-version', [str(IV), '-B', str(IVL), '-V'], 15, env)
    assert identity['native_exit'] == 0 and 'Icarus Verilog version 12.0' in Path(identity['log']).read_text()
    identity_vvp = h.stage(output, 'vvp-version', [str(VVP), '-V'], 15, env)
    assert identity_vvp['native_exit'] == 0

rows = []
resource_failure = None
for case, name in enumerate(PROFILE_NAMES):
    try:
        g = guard()
    except RuntimeError as error:
        resource_failure = str(error)
        break
    d = output / f'{case}-{name}'
    d.mkdir()
    definitions = [f'CASE={case}']
    if case == 2:
        definitions.append('FINISH_TASK')
    if case == 3:
        definitions.append('FINISH_FUNCTION')
    if case == 7:
        definitions.append('FINAL_STOP')
    mem = h.cg_events()
    row = {'case': case, 'id': name, 'definitions': definitions, 'resource_before': g, 'memory_events_before': mem}
    if args.phase == 'reference':
        c = h.stage(d, 'compile', [str(IV), '-B', str(IVL), '-g2012', '-s', 't', '-o', str(d / 'simulation.vvp'),
                                   *['-D' + v for v in definitions], str(C / 'finish_controls.sv')], 30, env)
        row['compile'] = c
        if c['native_exit'] == 0:
            row['run'] = h.stage(d, 'run', [str(VVP), '-n', str(d / 'simulation.vvp')], 10, env)
    else:
        obj = d / 'obj'
        c = h.stage(d, 'compile', [str(BIN), '--cc', '--exe', '--main', '--fourstate', '-Wno-FUTURE', '--timing', '--trace',
                                  '--prefix', 'Vt', '--top-module', 't', '--Mdir', str(obj),
                                  *['+define+' + v for v in definitions], str(C / 'finish_controls.sv')], 30, env)
        row['compile'] = c
        if c['native_exit'] == 0:
            row['build'] = h.stage(d, 'build', ['/usr/bin/make', '-C', str(obj), '-f', 'Vt.mk', '-j1', 'VM_PARALLEL_BUILDS=0'], 60, env)
            if row['build']['native_exit'] == 0:
                row['run'] = h.stage(d, 'run', [str(obj / 'Vt'), '+verilator+quiet'], 10, env)
                row['binary_sha256'] = h.sha(obj / 'Vt')
        row['gch_count'] = len(list(obj.rglob('*.gch')))
        assert row['gch_count'] == 0
    if 'run' in row:
        row['check'] = check(row['run']['log'], case)
        row['wave'] = wave(d / 'wave.vcd')
    row['actual_native_stages'] = sum(k in row for k in ('compile', 'build', 'run'))
    row['strict_passed'] = 'run' in row and all(type(row[k]['native_exit']) is int and row[k]['native_exit'] == 0 for k in ('compile', 'build', 'run') if k in row) and row['check']['strict_output_passed']
    row['memory_events_after'] = h.cg_events()
    row['six_memory_events_unchanged'] = mem == row['memory_events_after']
    row['resource_after'] = guard()
    h.save(d / 'result.json', row)
    rows.append(row)
    print(json.dumps({'phase': args.phase, 'case': case, 'id': name,
                      'native': {k: row[k]['native_exit'] for k in ('compile', 'build', 'run') if k in row},
                      'strict_passed': row['strict_passed'], 'memory_delta_zero': row['six_memory_events_unchanged']}), flush=True)
    if not row['six_memory_events_unchanged']:
        resource_failure = 'Memory event delta: stopped before launching later cases'
        break
    if any(row[k]['timed_out'] or row[k]['wait4_maxrss_KiB'] > 768 * 1024 for k in ('compile', 'build', 'run') if k in row):
        resource_failure = 'Timeout or memory limit: stopped before launching later cases'
        break
after = {p: h.sha(p) for p in protected}
h.save(E / ('baseline-v2-protected-after.json'), after)
result = {'phase': args.phase, 'selected': 8, 'actual_cases': len(rows), 'NOTRUN': PROFILE_NAMES[len(rows):],
          'results': rows, 'native_model_stage_count': sum(r['actual_native_stages'] for r in rows),
          'strict_passed': sum(r['strict_passed'] for r in rows), 'strict_failed': sum(not r['strict_passed'] for r in rows),
          'resource_failure': resource_failure, 'protected_unchanged': after == protected,
          'memory_events_before': start_memory, 'memory_events_after': h.cg_events(), 'owned_bytes': size(),
          'compiler_builds': 0, 'default_runtime_only': True,
          'strict_gate_exit': 0 if len(rows) == 8 and all(r['strict_passed'] for r in rows) and after == protected and not resource_failure else 1}
h.save(E / ('baseline-v2-result.json'), result)
raise SystemExit(result['strict_gate_exit'])
