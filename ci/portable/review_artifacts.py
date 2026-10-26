#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Read selected same-run artifact bytes without executing producer programs."""
import argparse
from contextlib import redirect_stdout
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import re
import runpy
import struct
import subprocess
import sys
import tarfile

import check_results
import log_evidence
from run_regressions import GROUPS, parse_summary, passed_counts, passed_names
from run_thread_controls import NAMES

ROOT = Path(__file__).resolve().parents[2]
PIN = 'f45ffabed3212a106f01cb362ef42c5d293f4513'


def require(value, reason):
    """Use explicit exceptions, including when Python assertions are disabled."""
    if not value:
        raise ValueError(reason)


def sha(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream)


def git_head(root):
    return subprocess.check_output(
        ['git', '--no-optional-locks', '-C',
         str(root), 'rev-parse', 'HEAD'], text=True).strip()


def record_migration(args):
    """Record the existing Bash command's returned status, never invent wait4."""
    require(0 <= args.returned_status <= 255, 'invalid_shell_status')
    require(os.environ.get('GITHUB_RUN_ID', '').isdigit(), 'missing_run_id')
    require(os.environ.get('GITHUB_JOB') == 'macos', 'unexpected_producer_job')
    record = {
        'schema':
        'portable-migration-return-v1',
        'head':
        git_head(ROOT),
        'run_id':
        int(os.environ['GITHUB_RUN_ID']),
        'job':
        'macos',
        'run_attempt':
        int(os.environ.get('GITHUB_RUN_ATTEMPT', '1')),
        'recorded_utc':
        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'platform':
        'macos-arm64',
        'completed':
        True,
        'shell_returned_status':
        args.returned_status,
        'raw_wait_status':
        'NOT_RECORDED',
        'command': [
            'python3', 'ci/portable/smoke.py',
            '/tmp/verilator-relocated/verilator-fourstate/bin/verilator', '/tmp/portable-smoke'
        ],
        'script_sha256':
        sha(ROOT / 'ci/portable/smoke.py'),
        'package_sha256':
        sha(args.package),
        'relocated_compiler_sha256':
        sha(args.relocated_compiler),
    }
    destination = ROOT / 'out/migration-smoke.json'
    temporary = destination.with_suffix('.json.tmp')
    require(not destination.exists() and not temporary.exists(), 'existing_migration_record')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(record, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        temporary.rename(destination)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def package(main, platform, head):
    """Hash tar members and inspect headers; never extract or execute them."""
    archive = main / 'out' / ('verilator-fourstate-' + platform + '.tar.gz')
    digest = sha(archive)
    sums = (main / 'out/SHA256SUMS').read_text().splitlines()
    require([line for line in sums
             if line.endswith('  ' + archive.name)] == [digest + '  ' + archive.name],
            'package_manifest_mismatch')
    compiler_sum = (main / 'out/compiler-SHA256SUMS').read_text().splitlines()
    require(
        len(compiler_sum) == 1
        and re.fullmatch(r'[0-9a-f]{64}  bin/verilator_bin', compiler_sum[0]),
        'compiler_manifest_invalid')
    with tarfile.open(archive, 'r:gz') as bundle:
        names = bundle.getnames()
        member = 'verilator-fourstate/bin/verilator_bin'
        require(
            names.count(member) == 1 and bundle.getmember(member).isfile(),
            'compiler_member_invalid')
        result = hashlib.sha256()
        with bundle.extractfile(member) as stream:
            header = stream.read(32)
            result.update(header)
            for block in iter(lambda: stream.read(1048576), b''):
                result.update(block)
        compiler_sha = result.hexdigest()
        require(compiler_sum[0].startswith(compiler_sha + '  '), 'compiler_bytes_mismatch')
        provenance = 'verilator-fourstate/provenance.txt'
        require(
            names.count(provenance) == 1 and bundle.getmember(provenance).isfile(),
            'package_provenance_missing')
        require(
            bundle.extractfile(provenance).read().decode().splitlines()[0] == head,
            'package_head_mismatch')
    if platform == 'macos-arm64':
        require(
            len(header) == 32 and struct.unpack('<II', header[:8]) == (0xFEEDFACF, 0x0100000C),
            'not_thin_macho_arm64')
        architecture = 'Mach-O64 arm64'
    else:
        require(
            len(header) == 32 and header[:6] == b'\x7fELF\x02\x01'
            and struct.unpack('<H', header[18:20])[0] == 62, 'not_elf64_x86_64')
        architecture = 'ELF64 x86_64'
    return {
        'archive_sha256': digest,
        'compiler_sha256': compiler_sha,
        'header': architecture,
        'producer_program_executed': False
    }


def ast_evidence(main, source):
    """Use the unchanged generated-identifier normalizer on original bytes."""
    normalize = runpy.run_path(
        source / 'test_regress/vltest_generated_ids.py')['normalize_generated_identifiers']
    golden = normalize(
        (source / 'test_regress/t/t_debug_emitv.out').read_bytes().decode('latin1'))[0]
    paths = sorted((main / 'test_regress/obj_vlt/t_debug_emitv').glob('*_width.tree.v'))
    require(paths and sum(p.stat().st_size for p in paths) <= 128 * 1024,
            'missing_or_oversized_public_ast')
    records = [log_evidence.enum_evidence(path, main) for path in paths]
    require(records == read(main / 'out/enum-hash-evidence.json'), 'ast_manifest_mismatch')
    for path in paths:
        require(
            normalize(path.read_bytes().decode('latin1'))[0] == golden,
            'ast_original_golden_mismatch')
    return [{
        'raw_sha256': row['raw_sha256'],
        'normalized_sha256': row['normalized_sha256'],
        'golden_equal': True
    } for row in records]


def native(folder, label, producer_root, relative_log, relative_cwd):
    """Resolve only explicit known files; original absolute records stay intact."""
    result = read(folder / (label + '.finished.json'))
    started = read(folder / (label + '.started.json'))
    require(all(result.get(k) == v for k, v in started.items()), 'native_start_mismatch')
    require(
        result.get('schema') == 'native-process-wait4-v1' and type(result.get('pid')) is int
        and result['pid'] > 0 and result['pid'] == result.get('wait4_pid'), 'native_pid_invalid')
    require(
        type(result.get('actual_exit')) is int and type(result.get('raw_wait_status')) is int
        and os.waitstatus_to_exitcode(result['raw_wait_status']) == result['actual_exit'],
        'native_exit_invalid')
    raw = result['raw_wait_status']
    require(
        type(result.get('exited_normally')) is bool and type(result.get('kill_sent')) is bool,
        'native_status_type')
    if os.WIFEXITED(raw):
        require(
            result['exited_normally'] is True and type(result.get('exit_status')) is int
            and result['exit_status'] == result['actual_exit'] and result['signal'] is None,
            'native_normal_exit_mismatch')
    else:
        require(
            os.WIFSIGNALED(raw) and result['exited_normally'] is False
            and result['exit_status'] is None and type(result.get('signal')) is int
            and result['signal'] == os.WTERMSIG(raw), 'native_signal_mismatch')
    require(
        result.get('termination_reason') in (None, 'timeout', 'disk_guard')
        and (not result['kill_sent'] or result['termination_reason'] is not None),
        'native_termination_mismatch')
    require(
        result['log'] == producer_root + '/' + relative_log
        and result['cwd'] == producer_root + '/' + relative_cwd, 'native_path_mismatch')
    log = folder / (label + '.log')
    require(result['log_sha256'] == sha(log) and result['log_bytes'] == log.stat().st_size,
            'native_log_mismatch')
    return result


def thread_evidence(main, source, head):
    folder = main / 'out/thread-controls'
    result = read(folder / 'results.json')
    record = read(folder / 'run.finished.json')
    suffix = '/out/thread-controls/run.log'
    require(record['log'].endswith(suffix), 'thread_log_location_invalid')
    producer = record['log'][:-len(suffix)]
    record = native(folder, 'run', producer, suffix[1:], 'test_regress')
    text = (folder / 'run.log').read_text()
    status, counts = parse_summary(text)
    names = re.findall(r'^vltmt/(t_[A-Za-z0-9_]+): Self PASSED$', text, re.MULTILINE)
    require(
        result['commit'] == head and result['selected'] == list(NAMES)
        and result['actual_pass_names'] == names and result['counts'] == counts
        and result['summary_status'] == status, 'thread_record_mismatch')
    complete = passed_counts(status, counts, 6) and len(names) == len(set(names)) == 6
    require(set(names) <= {'t_' + name for name in NAMES}, 'unexpected_thread_name')
    # native_process returns 128 + signal to its caller after preserving wait4.
    wrapper_exit = record['actual_exit'] if record[
        'actual_exit'] >= 0 else 128 - record['actual_exit']
    require(
        type(result['returncode']) is int and result['returncode'] == wrapper_exit
        and type(result['success']) is bool
        and result['success'] == (wrapper_exit == 0 and complete), 'thread_return_mismatch')
    semantic = (record['actual_exit'] != 0 or record['termination_reason'] is not None
                or record['kill_sent'] or not record['exited_normally'] or not complete)
    verify = runpy.run_path(source / 'test_regress/t/mt_trace_oracle.py')['verify']
    waves = []
    for name, fourstate in [('two_state', False), ('four_state', True)]:
        directory = main / 'test_regress/obj_vltmt/t_fourstate_mt_trace' / name
        wave = verify(directory / 'run.log', directory / 'simx.vcd', fourstate)
        waves.append({
            'profile': name,
            'histories': wave['complete_histories'],
            'records': wave['complete_records'],
            'sha256': sha(directory / 'simx.vcd')
        })
    return {
        'passed_names': len(names),
        'counts': counts,
        'waves': waves,
        'native_exit': record['actual_exit'],
        'scope': 'bytes_and_original_oracle'
    }, producer, semantic


def ram_evidence(main, source, head, producer):
    directory = main / 'out/ram-matrix/original'
    oracle = read(directory / 'oracle.json')
    functions = runpy.run_path(source / 'ci/portable/ram-matrix-original/verify_matrix.py')
    reports = {}
    for line in (directory / 'run.log').read_text().splitlines():
        match = functions['REPORT'].fullmatch(line)
        if not match:
            require(not line.startswith('ARRAY_TMP'), 'malformed_ram_report')
            continue
        key = tuple(map(int, match.groups()[:4]))
        require(key not in reports, 'duplicate_ram_report')
        reports[key] = {
            'words': list(match.groups()[4:7]),
            'side_effects': int(match[8]),
            'checks': int(match[9])
        }
        require(reports[key] == functions['report_expected'](key[0], key[3]),
                'ram_literal_mismatch')
    required = {(w, u, p, phase) for w, u, p in functions['LANES'].values() for phase in range(14)}
    require(set(reports) == required and oracle['label'] == head, 'ram_selection_mismatch')
    expected = functions['expected_histories']()
    actual = functions['parse_vcd'](directory / 't_fourstate_array_tmp.vcd', expected)
    require(
        oracle['expected_histories'] == expected and oracle['actual_histories'] == actual
        and oracle['assertions_total'] == 318 and oracle['phase_reports'] == 84
        and oracle['complete_signal_histories'] == 30
        and oracle['complete_history_records'] == 228, 'ram_oracle_mismatch')
    require((directory / 'run.log').read_text().count('*-* All Finished *-*') == 1,
            'ram_finished_marker_invalid')
    failed = False
    for label in ('compile', 'build', 'run', 'check'):
        rel = 'out/ram-matrix/original'
        record = native(directory, label, producer, rel + '/' + label + '.log', rel)
        failed = (failed or record['actual_exit'] != 0 or record['termination_reason'] is not None
                  or record['kill_sent'] or not record['exited_normally'])
    return {
        'assertions': 318,
        'reports': len(reports),
        'histories': len(actual),
        'records': sum(map(len, actual.values())),
        'wave_sha256': sha(directory / 't_fourstate_array_tmp.vcd'),
        'scope': 'bytes_and_original_oracle'
    }, failed


def reported(main, pair, head):
    """These summaries are reported only, never a cross-host full checker claim."""
    full = read(main / 'out/icarus/check-full18.json')
    finish = read(main / 'out/finish9/check.json')
    paired = read(pair / 'RUN_SUMMARY.json')
    require(full['compiler_head'] == finish['commit'] == paired['verilator_head'] == head,
            'reported_head_mismatch')
    require(paired['pin'] == PIN, 'reported_icarus_pin_mismatch')
    gates = [full['full18_gate_exit'], finish['strict_gate_exit'], paired['overall_exit']]
    require(all(type(value) is int and value in (0, 1) for value in gates), 'reported_gate_type')

    def integer(value):
        require(type(value) is int and value >= 0, 'reported_count_type')
        return value

    def counts(value):
        require(
            isinstance(value, dict)
            and all(isinstance(key, str) and re.fullmatch(r'[A-Za-z0-9_]+', key) for key in value),
            'reported_counts_invalid')
        return {key: integer(number) for key, number in value.items()}

    full_counts = counts(full['counts'])
    selected = integer(full['selected'])
    require(sum(full_counts.values()) == selected, 'reported_full18_count_mismatch')
    finish_counts = {
        key: integer(finish[key])
        for key in ('selected', 'executed', 'passed', 'failed')
    }
    require(finish_counts['passed'] + finish_counts['failed'] == finish_counts['executed'],
            'reported_finish_count_mismatch')
    paired_counts = counts(paired['pair_status_counts'])
    fixed = integer(paired['fixed_selected'])
    denominator = integer(paired['default_denominator'])
    remaining = integer(paired['unselected_UNRUN'])
    require(
        type(paired['full_suite_complete']) is bool and sum(paired_counts.values()) == fixed
        and fixed + remaining == denominator and paired['full_suite_complete'] == (remaining == 0),
        'reported_pair_count_mismatch')
    return {
        'scope': 'producer_reported_not_independently_recomputed',
        'full18_gate_exit': gates[0],
        'finish9_gate_exit': gates[1],
        'fixed128_overall_exit': gates[2],
        'full18': {
            'selected': selected,
            'counts': full_counts
        },
        'finish9': finish_counts,
        'fixed128': {
            'fixed_selected': fixed,
            'default_denominator': denominator,
            'pair_status_counts': paired_counts,
            'unselected_UNRUN': remaining,
            'full_suite_complete': paired['full_suite_complete']
        }
    }, any(gates)


def review_platform(main, pair, source, platform, head, run_id, needs):
    require(needs in ('success', 'failure'), 'producer_job_not_completed')
    require((main / 'out/provenance.txt').read_text().splitlines()[0] == head,
            'artifact_head_mismatch')
    groups = read(main / 'out/regression-results.json')
    require(set(groups) == set(GROUPS), 'missing_regression_group')
    for name, row in groups.items():
        require(
            row['commit'] == head and row['selected'] == GROUPS[name]
            and type(row['expected']) is int and row['expected'] == len(GROUPS[name])
            and type(row['returncode']) is int and type(row['success']) is bool
            and all(type(n) is int for n in row['counts'].values()), 'regression_record_type')
        text = (main / 'logs' / (name + '-regressions.log')).read_text()
        status, counts = parse_summary(text)
        require(status == row['summary_status'] and counts == row['counts'],
                'regression_count_mismatch')
        require(
            row['success'] == (row['returncode'] == 0
                               and passed_counts(status, counts, len(GROUPS[name]))
                               and passed_names(text, GROUPS[name])),
            'regression_success_mismatch')
    semantic = needs == 'failure'
    try:
        with redirect_stdout(io.StringIO()):
            check_results.check_results(main)
    except SystemExit as error:
        if str(error).startswith('Failed or incomplete regression group: '):
            semantic = True
        else:
            raise ValueError('regression_evidence_invalid') from error
    result = {
        'producer_job_result': needs,
        'groups': len(GROUPS),
        'selected_drivers': sum(map(len, GROUPS.values())),
        'package': package(main, platform, head),
        'public_ast': ast_evidence(main, source)
    }
    result['threads'], producer, failed = thread_evidence(main, source, head)
    semantic = semantic or failed
    result['ram'], failed = ram_evidence(main, source, head, producer)
    semantic = semantic or failed
    if platform == 'macos-arm64':
        migration = read(main / 'out/migration-smoke.json')
        require(
            migration['schema'] == 'portable-migration-return-v1' and migration['head'] == head
            and type(migration['run_id']) is int and migration['run_id'] == run_id
            and migration['job'] == 'macos' and type(migration['run_attempt']) is int
            and migration['run_attempt'] == int(os.environ.get('GITHUB_RUN_ATTEMPT', '1'))
            and migration['platform'] == platform and migration['completed'] is True
            and type(migration['shell_returned_status']) is int
            and 0 <= migration['shell_returned_status'] <= 255
            and migration['raw_wait_status'] == 'NOT_RECORDED'
            and migration['script_sha256'] == sha(source / 'ci/portable/smoke.py')
            and migration['package_sha256'] == result['package']['archive_sha256']
            and migration['relocated_compiler_sha256'] == result['package']['compiler_sha256']
            and migration['command'] == [
                'python3', 'ci/portable/smoke.py',
                '/tmp/verilator-relocated/verilator-fourstate/bin/verilator', '/tmp/portable-smoke'
            ], 'migration_record_mismatch')
        result['migration'] = {
            'scope': 'direct_producer_shell_return',
            'returned_status': migration['shell_returned_status'],
            'raw_wait_status': 'NOT_RECORDED'
        }
        semantic = semantic or migration['shell_returned_status'] != 0
    else:
        result['migration'] = {'scope': 'not_recomputed_by_linux_review'}
    result['other_gates'], failed = reported(main, pair, head)
    return result, semantic or failed


def review(args):
    require(not sys.flags.optimize, 'optimized_python_not_supported')
    require(git_head(ROOT) == args.expected_head, 'review_checkout_head_mismatch')
    result = {
        'schema': 'portable-artifact-core-review-v1',
        'head': args.expected_head,
        'run_id': args.run_id,
        'audit_integrity': args.downloads_ok == 'true',
        'semantic_gate_exit': int(args.macos_result == 'failure'
                                  or args.rocky8_result == 'failure'),
        'platforms': {},
        'core_scope': 'counts_public_ast_package_RAM_MT',
        'full18_finish_pair_scope': 'producer_reported_only',
        'artifact_zip_transport_digest': 'NOT_INDEPENDENTLY_VERIFIED',
        'producer_programs_executed': False
    }
    for name, platform, needs in [('mac', 'macos-arm64', args.macos_result),
                                  ('rocky', 'rocky8-x86_64', args.rocky8_result)]:
        try:
            data, failed = review_platform(args.artifacts / (name + '-main'),
                                           args.artifacts / (name + '-pair'), ROOT, platform,
                                           args.expected_head, args.run_id, needs)
            result['platforms'][platform] = data
            result['semantic_gate_exit'] |= int(failed)
        except (OSError, ValueError, KeyError, AssertionError, TypeError, IndexError,
                AttributeError, EOFError, tarfile.TarError) as error:
            result['audit_integrity'] = False
            result['platforms'][platform] = {
                'integrity_error': type(error).__name__,
                'reason': str(error)
                if re.fullmatch(r'[a-z0-9_]+', str(error)) else 'missing_or_invalid_evidence',
                'producer_job_result': needs
            }
    if result['audit_integrity']:
        result['cross_host_ast_equal'] = ([
            x['normalized_sha256'] for x in result['platforms']['macos-arm64']['public_ast']
        ] == [x['normalized_sha256'] for x in result['platforms']['rocky8-x86_64']['public_ast']])
        result['audit_integrity'] = result['cross_host_ast_equal']
    result['actual_exit'] = result['semantic_gate_exit'] if result['audit_integrity'] else 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print('PORTABLE_ARTIFACT_REVIEW ' + json.dumps(result, sort_keys=True))
    print('PORTABLE_ARTIFACT_REVIEW_SHA256 ' + sha(args.output))
    return result['actual_exit']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    record = commands.add_parser('record-migration')
    record.add_argument('--returned-status', required=True, type=int)
    record.add_argument('--package', required=True, type=Path)
    record.add_argument('--relocated-compiler', required=True, type=Path)
    check = commands.add_parser('review')
    check.add_argument('--expected-head', required=True)
    check.add_argument('--run-id', required=True, type=int)
    check.add_argument('--artifacts', required=True, type=Path)
    check.add_argument('--output', required=True, type=Path)
    check.add_argument('--macos-result', required=True)
    check.add_argument('--rocky8-result', required=True)
    check.add_argument('--downloads-ok', choices=('true', 'false'), required=True)
    args = parser.parse_args()
    if args.action == 'record-migration':
        record_migration(args)
        return 0
    try:
        return review(args)
    except (OSError, ValueError, KeyError, AssertionError, TypeError, IndexError, AttributeError,
            EOFError, tarfile.TarError):
        print('PORTABLE_ARTIFACT_REVIEW ' + json.dumps({
            'audit_integrity': False,
            'actual_exit': 2,
            'reason': 'review_preflight_failed'
        }))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
