#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Run the pinned official Icarus subset without changing sources or expectations.

All 18 cases execute. The explicitly documented 16-case acceptance gate is
separate from the two diagnostic-only cases and the existing portable suite.
"""

import argparse
import hashlib
import json
import os
import re
import resource
import signal
import ssl
import subprocess
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path, PurePosixPath

PIN = 'f45ffabed3212a106f01cb362ef42c5d293f4513'
IDS = ('addwide', 'unary_minus', 'unary_minus3', 'shift1', 'shift5', 'signed4', 'tern1', 'tern5',
       'tern10', 'muxtest', 'nb_assign', 'nb_delay', 'nb_ec_concat', 'assign_nb1', 'packeda',
       'sv_packed_port1', 'sv_cast_packed_struct', 'always_comb')
DIAGNOSTIC_IDS = {'nb_ec_concat', 'sv_packed_port1'}
SOURCE_ROOT = Path(__file__).resolve().parents[2]
CONTRACT = Path(__file__).with_name('icarus_contract.json')


def sha(path):
    """Hash file bytes, including the original expected transcript bytes."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    """Atomically replace only this run's owned progress/receipt file."""
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    os.replace(temporary, path)


def relative_path(name):
    """Reject absolute or escaping downloaded contract paths."""
    path = PurePosixPath(name)
    if path.is_absolute() or '..' in path.parts or not path.parts or '\\' in name:
        raise ValueError('Invalid official relative path: ' + name)
    return path


def load_contract(path):  # pylint: disable=too-many-branches
    """Require the frozen 18 identities, original expectations and 16 gate."""
    contract = json.loads(path.read_text())
    profiles = contract['profiles']
    if contract['source_commit'] != PIN or tuple(p['id'] for p in profiles) != IDS:
        raise ValueError('Official pin or complete ordered selection differs')
    if set(contract['diagnostic_only']) != DIAGNOSTIC_IDS or len(contract['diagnostic_only']) != 2:
        raise ValueError('Diagnostic exclusions differ from the documented two cases')
    gate = [p['id'] for p in profiles if p['id'] not in DIAGNOSTIC_IDS]
    if contract['applicable'] != gate or len(gate) != 16:
        raise ValueError('Applicable selection must retain all original 16 cases')
    modes = Counter(p['expected']['mode'] for p in profiles)
    if modes != {'original_gold_exact': 4, 'upstream_selfchecking_unique_PASSED': 14}:
        raise ValueError('Original gold/self-check contract differs')
    for name, record in contract['files'].items():
        relative_path(name)
        if not re.fullmatch(r'[0-9a-f]{64}', record['sha256']):
            raise ValueError('Invalid official file digest')
    for profile in profiles:
        source = profile['source']
        if contract['files'][source]['sha256'] != profile['source_sha256']:
            raise ValueError('Profile source hash differs from pinned file inventory')
        expected = profile['expected']
        if (expected['mode'] == 'original_gold_exact'
                and contract['files'][expected['path']]['sha256'] != expected['sha256']):
            raise ValueError('Original golden hash differs')
        if profile['verilator_flags'] != [
                '--cc', '--exe', '--main', '--fourstate', '--timing', '-Wno-fatal', '-CFLAGS',
                '-DVL_USER_FINISH'
        ] or profile['runtime_flags'] != ['+verilator+quiet']:
            raise ValueError('Original candidate flags changed')
    if len(contract['files']) != 29 or not {'COPYING', 'ivtest/COPYING'}.issubset(
            contract['files']):
        raise ValueError('Incomplete official inputs or license inventory')
    hook = contract['finish_hook']
    if hashlib.sha256(hook['source'].encode()).hexdigest() != hook['sha256']:
        raise ValueError('Documented finish hook bytes differ')
    return contract


def error_headers(text):
    """Retain every primary Error/Fatal header, including mixed diagnostics."""
    return [
        line for line in text.splitlines() if re.match(r'^(?:%Error|(?:\[[^\]]+\] )?%Fatal)', line)
    ]


class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    """Keep certificate-verified official downloads on HTTPS."""

    # Match urllib's public override signature.
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # pylint: disable=too-many-arguments,too-many-positional-arguments
        parsed = urllib.parse.urlsplit(newurl)
        if parsed.scheme != 'https' or parsed.hostname != 'raw.githubusercontent.com':
            raise ValueError('Refuse nonofficial or non-HTTPS redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def verify_files(contract, cache, download=False):
    """Fetch fixed-pin official bytes if needed and verify SHA256/Git blob IDs."""
    opener = urllib.request.build_opener(
        HTTPSRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context()))
    hashes = {}
    for name, expected in contract['files'].items():
        path = cache / str(relative_path(name))
        if not path.exists() and download:
            url = 'https://raw.githubusercontent.com/steveicarus/iverilog/' + PIN + '/' + name
            with opener.open(url, timeout=30) as response:
                content = response.read()
            if hashlib.sha256(content).hexdigest() != expected['sha256']:
                raise ValueError('Downloaded official file hash differs: ' + name)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('xb') as stream:
                stream.write(content)
        content = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        if sha(path) != expected['sha256'] or blob != expected['git_blob_SHA1']:
            raise ValueError('Official source/gold/license hash differs: ' + name)
        hashes[str(path)] = sha(path)
    return hashes


def stage(folder, label, command, timeout, env):  # pylint: disable=too-many-locals
    """Collect a real subprocess's full output, native exit and group timeout."""
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / (label + '.log')
    started = {
        'command': command,
        'cwd': str(folder),
        'timeout_seconds': timeout,
        'started_epoch': time.time(),
        'pid': None
    }
    expired = False
    launch_error = None
    native_exit = None
    try:
        with subprocess.Popen(command,
                              cwd=folder,
                              env=env,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              start_new_session=True) as child:
            started['pid'] = child.pid
            save(folder / (label + '.started.json'), started)
            try:
                output, _ = child.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                expired = True
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                output, _ = child.communicate()
            native_exit = child.returncode
    except OSError as error:
        launch_error = str(error)
        output = ('Subprocess launch failed: ' + launch_error + '\n').encode()
        save(folder / (label + '.started.json'), started)
    with log.open('xb') as stream:
        stream.write(output)
    text = output.decode(errors='replace')
    record = dict(started,
                  finished_epoch=time.time(),
                  native_exit=native_exit,
                  timed_out=expired,
                  launch_error=launch_error,
                  log=str(log),
                  log_sha256=sha(log),
                  error_headers=error_headers(text),
                  warning_headers=dict(
                      Counter(re.findall(r'^%(Warning-[^:]+):', text, re.MULTILINE))))
    save(folder / (label + '.finished.json'), record)
    return record


def stage_ok(record):
    """Reject nonzero, launch failures, timeouts and boolean-valued exits."""
    # bool is an int subclass; native process exit codes must actually be integers.
    return bool(record and type(record['native_exit']) is int  # pylint: disable=unidiomatic-typecheck
                and record['native_exit'] == 0 and record['timed_out'] is False
                and record['launch_error'] is None and not record['error_headers'])


def output_check(log, profile, cache):
    """Check all original SV stdout; the sole adaptation is upstream's CRLF."""
    raw = Path(log).read_bytes().replace(b'\r\n', b'\n')
    text = raw.decode(errors='replace')
    failure = bool(
        re.search(r'(?im)\bFAIL(?:ED|URE)?\b|\bFATAL\b|(?:^|\s)(?:%Error|ERROR[:\s])', text))
    expected = profile['expected']
    if expected['mode'] == 'original_gold_exact':
        golden = cache / expected['path']
        if sha(golden) != expected['sha256']:
            raise ValueError('Original golden bytes changed')
        equal = raw == golden.read_bytes().replace(b'\r\n', b'\n')
        return {
            'passed': equal and not failure,
            'exact_equal': equal,
            'failure_output_detected': failure,
            'mode': expected['mode']
        }
    count = sum(
        bool(re.fullmatch(r'\s*passed\s*', line, re.IGNORECASE)) for line in text.splitlines())
    return {
        'passed': count == 1 and not failure,
        'standalone_PASSED_count': count,
        'failure_output_detected': failure,
        'mode': expected['mode']
    }


def classify(row, profile, cache):
    """Derive status from actual stages and stdout rather than reported success."""
    compile_step, build, run = (row[name] for name in ('compile', 'build', 'run'))
    if not stage_ok(compile_step):
        primary = [
            line for line in compile_step['error_headers']
            if not re.fullmatch(r'%Error: Exiting due to \d+ (?:error|warning)\(s\)', line)
        ]
        if compile_step['timed_out']:
            return 'compile_timeout'
        if primary and all(line.startswith('%Error-UNSUPPORTED:') for line in primary):
            return 'compile_unsupported'
        return 'compile_failed'
    if not stage_ok(build):
        return 'build_timeout' if build and build['timed_out'] else 'build_failed'
    if not stage_ok(run):
        return 'runtime_timeout' if run and run['timed_out'] else 'runtime_failed'
    return 'passed' if output_check(run['log'], profile,
                                    cache)['passed'] else 'expected_output_failed'


def identity(repository, expected_head, compiler):
    """Bind compiler bytes/version and every tracked src/include file to HEAD."""
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repository, text=True).strip()
    if head != expected_head or not re.fullmatch(r'[0-9a-f]{40}', expected_head):
        raise ValueError('Candidate repository HEAD differs')
    version = subprocess.check_output([str(compiler), '--version'], text=True, timeout=15).strip()
    if head[:9] not in version or '(mod)' in version:
        raise ValueError('Compiler version is not the clean candidate HEAD')
    names = subprocess.check_output(['git', 'ls-files', '-z', 'src', 'include', 'bin'],
                                    cwd=repository)
    protected = {str(compiler): sha(compiler)}
    categories = Counter()
    for name in names.decode().split('\0'):
        if not name:
            continue
        original = subprocess.check_output(['git', 'show', head + ':' + name], cwd=repository)
        path = repository / name
        expected = hashlib.sha256(original).hexdigest()
        if sha(path) != expected:
            raise ValueError('Candidate tracked source differs: ' + name)
        protected[str(path)] = expected
        categories['bin' if name.startswith('bin/') else 'source'] += 1
    return {
        'compiler_head': head,
        'compiler_version': version,
        'compiler_sha256': sha(compiler),
        'source_files_commit_verified': categories['source'],
        'bin_helpers_commit_verified': categories['bin']
    }, protected


def runtime_files(repository):
    """Include configured make/config files and bin helpers, with dynamic counts."""
    return {
        str(path): sha(path)
        for directory in ('include', 'bin')
        for path in (repository / directory).rglob('*') if path.is_file()
    }


def strict_equal(actual, expected):
    """Keep integer-valued counts/gates distinct from JSON boolean values."""
    if type(actual) is not type(expected):  # pylint: disable=unidiomatic-typecheck
        return False
    if isinstance(expected, dict):
        return (actual.keys() == expected.keys()
                and all(strict_equal(actual[key], value) for key, value in expected.items()))
    return actual == expected


# These six inputs identify distinct immutable compile/build/run resources.
def commands(profile, compiler, cache, helper, folder, make):  # pylint: disable=too-many-arguments,too-many-positional-arguments
    """Use original flags plus forced generation and an isolated model directory."""
    return {
        'compile': [
            str(compiler), *profile['verilator_flags'], '--no-skip-identical', '--prefix', 'Vt',
            '--top-module', profile['top'], '--Mdir',
            str(folder / 'obj'),
            str(cache / profile['source']),
            str(helper)
        ],
        'build': [make, '-C', 'obj', '-f', 'Vt.mk', '-j1'],
        'run': [str(folder / 'obj/Vt'), *profile['runtime_flags']]
    }


def verify_record(record, expected_command, folder, label):
    """Re-read native receipts and unfiltered logs, including exact argv."""
    log = folder / (label + '.log')
    started = json.loads((folder / (label + '.started.json')).read_text())
    finished = json.loads((folder / (label + '.finished.json')).read_text())
    if not strict_equal(finished, record) or any(not strict_equal(record[key], value)
                                                 for key, value in started.items()):
        raise ValueError('Native started/finished receipt differs')
    if (record['command'] != expected_command or record['cwd'] != str(folder)
            or record['log'] != str(log) or record['log_sha256'] != sha(log)):
        raise ValueError('Native command/log provenance differs')
    if (record['finished_epoch'] < record['started_epoch'] or record['timeout_seconds'] <= 0
            or not isinstance(record['timed_out'], bool)):
        raise ValueError('Malformed native timing record')
    if record['native_exit'] is not None and type(record['native_exit']) is not int:  # pylint: disable=unidiomatic-typecheck
        raise ValueError('Native exit must be an integer, never bool')
    text = log.read_text(errors='replace')
    headers = error_headers(text)
    warnings = dict(Counter(re.findall(r'^%(Warning-[^:]+):', text, re.MULTILINE)))
    if record['error_headers'] != headers or record['warning_headers'] != warnings:
        raise ValueError('Original diagnostics differ from recorded headers')


# Keep one strict audit of selection, native stages, stdout and provenance.
def verify(output, contract_path, repository, expected_head, compiler):  # pylint: disable=too-many-locals,too-many-branches
    """Independently recompute all 18 results and the distinct 16-case gate."""
    contract = load_contract(contract_path)
    result = json.loads((output / 'result.json').read_text())
    current, source_protected = identity(repository, expected_head, compiler)
    if any(not strict_equal(result[key], value) for key, value in current.items()):
        raise ValueError('Compiler/source identity differs from run')
    if result['contract_sha256'] != sha(contract_path) or result['runner_sha256'] != sha(__file__):
        raise ValueError('Runner/contract provenance changed')
    before = json.loads((output / 'protected-before.json').read_text())
    after = json.loads((output / 'protected-after.json').read_text())
    if before != after or any(sha(path) != value for path, value in before.items()):
        raise ValueError('Protected source/compiler/runtime/upstream bytes changed')
    cache = Path(result['upstream_root'])
    required_protected = dict(source_protected, **verify_files(contract, cache))
    required_protected.update({
        str(contract_path.resolve()): sha(contract_path),
        str(Path(__file__).resolve()): sha(__file__),
        str(output / 'quiet_finish.cpp'): contract['finish_hook']['sha256']
    })
    required_protected.update(runtime_files(repository))
    for original, name in [('COPYING', 'root-COPYING'), ('ivtest/COPYING', 'ivtest-COPYING')]:
        required_protected[str(output / 'licenses' / name)] = contract['files'][original]['sha256']
    if before != required_protected:
        raise ValueError('Protection inventory is missing or contains changed inputs')
    if result['collection_complete'] is not True or tuple(row['id']
                                                          for row in result['results']) != IDS:
        raise ValueError('Missing, duplicate or unrun official case')
    all_counts, gate_counts, native_counts = Counter(), Counter(), Counter()
    rows = []
    for profile, row in zip(contract['profiles'], result['results']):
        folder = output / 'logs' / profile['id']
        expected_commands = commands(profile, compiler, cache, output / 'quiet_finish.cpp', folder,
                                     result['make'])
        previous_ok = True
        for label in ('compile', 'build', 'run'):
            step = row[label]
            if previous_ok and step is None or not previous_ok and step is not None:
                raise ValueError('Dependent stage was omitted or unexpectedly executed')
            if step is None:
                native_counts[label + '_unrun'] += 1
            else:
                verify_record(step, expected_commands[label], folder, label)
                native_counts[label + '_exit_' + str(step['native_exit'])] += 1
                native_counts['timed_out'] += int(step['timed_out'])
            previous_ok = stage_ok(step)
        status = classify(row, profile, cache)
        if row['status'] != status:
            raise ValueError('Reported status differs from actual native/stdout result')
        all_counts[status] += 1
        applicable = profile['id'] not in DIAGNOSTIC_IDS
        if applicable:
            gate_counts[status] += 1
        rows.append({
            'id':
            profile['id'],
            'status':
            status,
            'applicable':
            applicable,
            'output':
            output_check(row['run']['log'], profile, cache) if row['run'] else None
        })
    diagnostic_errors = [
        row['id'] for row in rows
        if not row['applicable'] and row['status'] not in ('passed', 'expected_output_failed')
    ]
    strict_exit = int(gate_counts != {'passed': 16} or bool(diagnostic_errors))
    all_exit = int(all_counts != {'passed': 18})
    expected = {
        'selected': 18,
        'applicable_selected': 16,
        'diagnostic_only_selected': 2,
        'skipped_selected': 0,
        'unrun_selected': 0,
        'counts': dict(all_counts),
        'applicable_counts': dict(gate_counts),
        'strict_gate_exit': strict_exit,
        'full18_gate_exit': all_exit,
        'native_counts': dict(native_counts),
        'failed_selected': 18 - all_counts.get('passed', 0),
        'applicable_failed': 16 - gate_counts.get('passed', 0),
        'diagnostic_infrastructure_failures': diagnostic_errors,
        'reference_stages_executed': 0,
        'official_input_files_verified': 29,
        'artifact_license_copies': 2,
        'runtime_files_protected': len(runtime_files(repository))
    }
    if any(not strict_equal(result[key], value) for key, value in expected.items()):
        raise ValueError('Recorded counts/gate differ from actual complete collection')
    return dict(expected,
                compiler_head=expected_head,
                compiler_sha256=sha(compiler),
                rows=rows,
                actual_receipts_logs_and_protection_verified=True,
                result_sha256=sha(output / 'result.json'),
                output_filtering='NONE; upstream CRLF only')


# Keep protection, complete collection and final gate in one auditable sequence.
def collect(args):  # pylint: disable=too-many-locals,too-many-statements
    """Attempt every selected compile and collect all dependent native stages."""
    contract = load_contract(args.contract)
    compiler = args.compiler.resolve()
    repository = args.repository.resolve()
    output = args.output.resolve()
    cache = args.upstream_root.resolve()
    current, protected = identity(repository, args.expected_head, compiler)
    protected.update(verify_files(contract, cache, download=True))
    protected.update({
        str(args.contract.resolve()): sha(args.contract),
        str(Path(__file__).resolve()): sha(__file__)
    })
    protected.update(runtime_files(repository))
    output.mkdir(parents=True, exist_ok=False)
    helper = output / 'quiet_finish.cpp'
    helper.write_text(contract['finish_hook']['source'])
    if sha(helper) != contract['finish_hook']['sha256']:
        raise ValueError('Runtime finish hook changed')
    protected[str(helper)] = sha(helper)
    licenses = output / 'licenses'
    licenses.mkdir()
    for original, name in [('COPYING', 'root-COPYING'), ('ivtest/COPYING', 'ivtest-COPYING')]:
        path = licenses / name
        path.write_bytes((cache / original).read_bytes())
        protected[str(path)] = contract['files'][original]['sha256']
    save(output / 'protected-before.json', protected)
    rows = []
    env = dict(os.environ, VERILATOR_ROOT=str(repository))
    for profile in contract['profiles']:
        folder = output / 'logs' / profile['id']
        argv = commands(profile, compiler, cache, helper, folder, args.make)
        row = {'id': profile['id'], 'compile': None, 'build': None, 'run': None}
        for label, timeout in [('compile', 30), ('build', 60), ('run', 15)]:
            row[label] = stage(folder, label, argv[label], timeout, env)
            if not stage_ok(row[label]):
                break
        row['status'] = classify(row, profile, cache)
        rows.append(row)
        save(output / 'progress.json', dict(current, results=rows, collection_complete=False))
    after = {path: sha(path) for path in protected}
    save(output / 'protected-after.json', after)
    if after != protected:
        raise ValueError('Protected bytes changed during execution')
    final_identity, _ = identity(repository, args.expected_head, compiler)
    if final_identity != current:
        raise ValueError('Candidate identity changed during execution')
    all_counts = Counter(row['status'] for row in rows)
    gate_counts = Counter(row['status'] for row in rows if row['id'] not in DIAGNOSTIC_IDS)
    native_counts = Counter()
    for row in rows:
        for label in ('compile', 'build', 'run'):
            record = row[label]
            native_counts[label + ('_unrun' if record is None else '_exit_' +
                                   str(record['native_exit']))] += 1
            if record:
                native_counts['timed_out'] += int(record['timed_out'])
    diagnostic_errors = [
        row['id'] for row in rows
        if row['id'] in DIAGNOSTIC_IDS and row['status'] not in ('passed',
                                                                 'expected_output_failed')
    ]
    result = dict(current,
                  results=rows,
                  collection_complete=True,
                  upstream_commit=PIN,
                  upstream_root=str(cache),
                  contract_sha256=sha(args.contract),
                  runner_sha256=sha(__file__),
                  make=args.make,
                  selected=18,
                  applicable_selected=16,
                  diagnostic_only_selected=2,
                  skipped_selected=0,
                  unrun_selected=0,
                  counts=dict(all_counts),
                  applicable_counts=dict(gate_counts),
                  native_counts=dict(native_counts),
                  strict_gate_exit=int(gate_counts != {'passed': 16} or bool(diagnostic_errors)),
                  full18_gate_exit=int(all_counts != {'passed': 18}),
                  failed_selected=18 - all_counts.get('passed', 0),
                  applicable_failed=16 - gate_counts.get('passed', 0),
                  diagnostic_infrastructure_failures=diagnostic_errors,
                  reference_stages_executed=0,
                  official_input_files_verified=29,
                  artifact_license_copies=2,
                  runtime_files_protected=len(runtime_files(repository)),
                  scope='Bounded original official acceptance; not IEEE normative certification',
                  output_filtering='NONE; upstream CRLF only')
    save(output / 'result.json', result)
    audit = verify(output, args.contract, repository, args.expected_head, compiler)
    save(output / 'check-1.json', audit)
    print(json.dumps({key: value for key, value in audit.items() if key != 'rows'}))
    return audit['strict_gate_exit']


def main():
    """Run or independently audit this separate official acceptance gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['run', 'check'])
    parser.add_argument('--contract', type=Path, default=CONTRACT)
    parser.add_argument('--repository', type=Path, default=SOURCE_ROOT)
    parser.add_argument('--compiler', type=Path, default=SOURCE_ROOT / 'bin/verilator_bin')
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--upstream-root',
                        type=Path,
                        default=SOURCE_ROOT / '.ci-tools-src/icarus-official')
    parser.add_argument('--output', type=Path, default=SOURCE_ROOT / 'out/icarus')
    parser.add_argument('--make', default='make')
    args = parser.parse_args()
    try:
        # Set this inherited limit in the single-threaded CLI, avoiding preexec_fn.
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if args.action == 'run':
            return collect(args)
        audit = verify(args.output.resolve(), args.contract, args.repository.resolve(),
                       args.expected_head, args.compiler.resolve())
        receipt = args.output / 'check-2.json'
        if receipt.exists():
            raise FileExistsError('Refuse to overwrite independent audit')
        save(receipt, audit)
        print(json.dumps({key: value for key, value in audit.items() if key != 'rows'}))
        return audit['strict_gate_exit']
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        print('Official Icarus acceptance rejected: ' + str(error))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
