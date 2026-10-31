#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# Integer evidence counters must reject Python bool, an int subclass.
# pylint: disable=unidiomatic-typecheck
"""Replay withdrawn clocking expectations without making their failures pass."""

import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from run_regressions import parse_summary

BASE_SHA = "4272ac27fbcb061c2a542c51e0381b598ac23ebe"
REVERT_SHA = "c0b2894994ce468303b79e8ef901f633dd134f00"
ARCHIVE = Path("ci/portable/legacy/clocking-8925")
LEGACY_NAMES = ("clocking_output_iface", "clocking_output_unsup")
CLASSIFICATION = "INAPPLICABLE_REVERTED_CONTRACT"
ORIGINAL_SELECTOR_SHA256 = "665e70412e7e1a35b9c92758d67587975e152abbd17023a957657dfa2a4c9332"
ORIGINAL_GROUPS = ("fourstate", "integration", "upstream", "capabilities", "extended", "followup",
                   "readmem", "nba", "pull", "resolve", "amd-repair", "deassign", "finish_slice",
                   "plusargs", "finish_propagation", "upstream_sync_20261010", "icarus_semantics",
                   "upstream_sync_20261011", "strict_repairs_20261011", "finish_boundary_20261011",
                   "upstream_daily_20261012", "sv_controls_20261012", "upstream_daily_20261013",
                   "upstream_daily_20261014", "upstream_daily_20261014_followup",
                   "upstream_daily_20261015", "finish_coverage_20261015", "upstream_sync_20261017",
                   "sv_semantics_20261026", "fourstate_constructors_20261026",
                   "upstream_sync_20261026", "tri_storage_20261026", "optimizer_alias_20261026",
                   "upstream_late_20261026", "sv_read_string_20261026", "upstream_daily_20261029",
                   "upstream_daily_20261030", "upstream_daily_20261031")
# These hashes are independent of the editable archive manifest. Both match the
# original files deleted by upstream REVERT_SHA, not regenerated expectations.
FIXTURE_SHA256 = {
    "t_clocking_output_iface.py":
    "214d8e5b3952712e213fd38fcbcd8a553da8f915704054554acc940f207786e2",
    "t_clocking_output_iface.v":
    "924ee3e1ab3116f20ac68bc0ad740c68e1837d6a2fe7ee9ac766622c0ac17bba",
    "t_clocking_output_unsup.out":
    "b13128ed25e2d559a7f314b82af3010bc24025b7cc543ce1c9e015501136722b",
    "t_clocking_output_unsup.py":
    "1c956ddc9c698dcec50308421ba87022969f8a0486d52ae492ac1f59f9f06f06",
    "t_clocking_output_unsup.v": "4e1bce5607ecfed1fcfaddb21df8e35f5db6901a98fe51b6938dda610ec5b4de"
}
SOURCE_INPUTS = ("test_regress/driver.py", "test_regress/input.vc", "test_regress/Makefile",
                 "test_regress/Makefile_obj", "ci/portable/native_process.py",
                 "ci/portable/run_regressions.py", "ci/portable/clocking_legacy.py")


def require(condition, reason):
    """Reject incomplete evidence rather than assigning it an applicability."""
    if not condition:
        raise ValueError(reason)


def sha(data):
    """Digest exact bytes, without normalization."""
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    """Digest an input or retained log."""
    return sha(path.read_bytes())


def read(path):
    """Read one explicit JSON record."""
    return json.loads(path.read_text())


def write(path, data):
    """Publish a record once; reruns need a new output directory."""
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")


def git_head(repo):
    """Observe checkout identity without claiming binary build provenance."""
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()


def selector_sha(names):
    """Use the frozen build.bash order, including a final newline."""
    return sha(("\n".join(names) + "\n").encode())


def verify_archive(repo):  # pylint: disable=too-many-locals
    """Check the original selector, five original fixtures and raw427 records."""
    archive = repo / ARCHIVE
    data = read(archive / "manifest.json")
    require(
        data['schema'] == 'clocking-8925-archive-v1' and data['base_sha'] == BASE_SHA
        and data['upstream_revert_sha'] == REVERT_SHA, 'archive_identity_mismatch')
    names = data['original_selected_names']
    require(
        len(names) == len(set(names)) == 438
        and selector_sha(names) == data['original_selector_sha256'] == ORIGINAL_SELECTOR_SHA256
        and tuple(data['original_groups']) == ORIGINAL_GROUPS
        and data['original_legacy_names'] == list(LEGACY_NAMES)
        and data['original_selected_count'] == 438 and data['remaining_original_count'] == 436,
        'original_selection_mismatch')
    require(
        data['classification'] == CLASSIFICATION and data['semantic_pass'] is False
        and data['original_criteria_pass'] is False, 'archive_semantic_status_changed')
    rows = data['fixtures']
    require(
        len(rows) == 5 and {Path(row['archived_path']).name
                            for row in rows} == set(FIXTURE_SHA256),
        'archive_fixture_selection_mismatch')
    for row in rows:
        name = Path(row['archived_path']).name
        original = 'test_regress/t/' + name
        require(row['original_path'] == original and row['archived_path'] == 'fixtures/' + name,
                'archive_fixture_path_changed')
        path = archive / row['archived_path']
        raw = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        require(
            not path.is_symlink() and sha(raw) == row['sha256'] == FIXTURE_SHA256[name]
            and len(raw) == row['bytes'] and blob == row['upstream_git_blob'],
            'archive_fixture_bytes_changed')
        require(
            row['git_mode'] == ('100755' if name.endswith('.py') else '100644')
            and bool(path.stat().st_mode & 0o111) == name.endswith('.py'),
            'archive_fixture_mode_changed')
        require(not os.path.lexists(repo / original), 'canonical_legacy_path_present')
    require(set(data['historical_427']) == set(LEGACY_NAMES), 'historical_selection_mismatch')
    for name in LEGACY_NAMES:
        folder = archive / 'historical-427' / name
        files = data['historical_427'][name]
        require(
            set(files) == {
                'RESULT_V1.json', 'driver.started.json', 'driver.finished.json', 'driver.log.gz'
            }, 'historical_file_selection_mismatch')
        for filename, expected in files.items():
            raw = (folder / filename).read_bytes()
            expanded = gzip.decompress(raw) if filename.endswith('.gz') else raw
            require(
                sha(raw) == expected['sha256'] and len(raw) == expected['bytes']
                and sha(expanded) == expected['raw_sha256']
                and len(expanded) == expected['raw_bytes'], 'historical_bytes_changed')
        result = read(folder / 'RESULT_V1.json')
        receipt = read(folder / 'driver.finished.json')
        require(
            result['head'] == BASE_SHA and result['receipt'] == receipt
            and result['passed'] is False, 'historical_result_mismatch')
        verify_case(name, read(folder / 'driver.started.json'), receipt,
                    gzip.decompress((folder / 'driver.log.gz').read_bytes()))
    return data


def verify_case(name, started, receipt, raw, *, argv=None, cwd=None, log=None):  # pylint: disable=too-many-arguments
    """Verify actual wait4 failure plus the specific withdrawn expectation."""
    require(name in LEGACY_NAMES, 'unknown_legacy_case')
    require(all(receipt.get(key) == value for key, value in started.items()),
            'native_start_mismatch')
    require(
        receipt.get('schema') == 'native-process-wait4-v1' and type(receipt.get('pid')) is int
        and receipt['pid'] > 0 and receipt['pid'] == receipt.get('wait4_pid'),
        'native_pid_mismatch')
    require(
        type(receipt.get('raw_wait_status')) is int and type(receipt.get('actual_exit')) is int
        and os.waitstatus_to_exitcode(receipt['raw_wait_status']) == receipt['actual_exit']
        and os.WIFEXITED(receipt['raw_wait_status'])
        and receipt['actual_exit'] == receipt.get('exit_status') == 10
        and receipt['raw_wait_status'] == 2560 and receipt.get('exited_normally') is True
        and receipt.get('signal') is None and receipt.get('termination_reason') is None
        and receipt.get('kill_sent') is False, 'legacy_native_failure_changed')
    require(
        receipt.get('log_sha256') == sha(raw) and receipt.get('log_bytes') == len(raw),
        'native_log_mismatch')
    if argv is not None:
        require(
            receipt['argv'] == argv and receipt['cwd'] == str(cwd) and receipt['log'] == str(log),
            'native_invocation_mismatch')
    text = raw.decode('utf-8', errors='replace')
    status, counts = parse_summary(text)
    require(
        status == 'FAILED' and counts == {
            'passed': 0,
            'failed': 1
        } and not re.search(r'^vlt/[^\n]+: Self PASSED$', text, re.MULTILINE),
        'legacy_raw_criteria_changed')
    fingerprint = (
        r'^%Error: t/t_clocking_output_iface\.v:244:  got=0 exp=3 '
        r'\(pattern_i\.id !== expected\.id\)$' if name == LEGACY_NAMES[0] else
        r'^vlt/t_clocking_output_unsup: %Error: Exec of verilator ok, but expected to fail$')
    require(
        re.search(fingerprint, text, re.MULTILINE) is not None
        and not re.search(r'Internal Error|Segmentation fault', text),
        'legacy_failure_fingerprint_changed')
    return {
        'summary_status': status,
        'counts': counts,
        'actual_exit': receipt['actual_exit'],
        'raw_wait_status': receipt['raw_wait_status'],
        'semantic_pass': False,
        'fingerprint_verified': True,
        'log_sha256': sha(raw)
    }


def source_inputs(repo):
    """Bind replay to the exact checked harness and observer sources."""
    return {name: file_sha(repo / name) for name in SOURCE_INPUTS}


def compiler_inputs(compiler):
    """Record the executable and runtime inputs, not inferred build provenance."""
    root = compiler.parent.parent
    require(
        compiler.name == 'verilator_bin' and compiler.parent.name == 'bin'
        and os.access(compiler, os.X_OK), 'provide_built_bin_verilator_bin')
    runtime = {
        str(path.relative_to(root)): file_sha(path)
        for path in sorted((root / 'include').rglob('*')) if path.is_file()
    }
    require(runtime and 'include/verilated.mk' in runtime, 'compiler_runtime_missing')
    return {
        'path': str(compiler),
        'sha256': file_sha(compiler),
        'root': str(root),
        'checkout_head': git_head(root),
        'wrapper_sha256': file_sha(root / 'bin/verilator'),
        'runtime_sha256': sha(json.dumps(runtime, sort_keys=True).encode()),
        'binary_to_commit_provenance': 'NOT_INDEPENDENTLY_VERIFIED'
    }


def invocation(repo, python, name):
    """Run the original driver bytes through the original harness."""
    return [
        python,
        str(repo / 'test_regress/driver.py'), '--vlt', '-j1', '--no-skip-identical',
        't/t_' + name + '.py'
    ]


def audit(repo, output):  # pylint: disable=too-many-locals
    """Recompute evidence locally; saved audit.json is never an input."""
    repo, output = Path(repo).resolve(strict=True), Path(output).resolve(strict=True)
    manifest = verify_archive(repo)
    saved = read(output / 'results.json')
    head = git_head(repo)
    require(saved['schema'] == 'clocking-legacy-replay-v1' and saved['head'] == head,
            'legacy_replay_head_mismatch')
    require(
        saved['archive_manifest_sha256'] == file_sha(repo / ARCHIVE / 'manifest.json')
        and saved['source_inputs_before'] == saved['source_inputs_after'] == source_inputs(repo)
        and saved['golden_updates'] is False, 'legacy_replay_inputs_changed')
    compiler = compiler_inputs(Path(saved['compiler_before']['path']))
    require(saved['compiler_before'] == saved['compiler_after'] == compiler,
            'legacy_compiler_inputs_changed')
    harness = output / 'harness/test_regress'
    for name, expected in FIXTURE_SHA256.items():
        require(file_sha(harness / 't' / name) == expected, 'scratch_fixture_changed')
    for name in ('input.vc', 'Makefile'):
        require(
            file_sha(harness / name) == file_sha(repo / 'test_regress' / name),
            'scratch_harness_changed')
    require(set(saved['cases']) == set(LEGACY_NAMES), 'legacy_replay_selection_changed')
    cases = {}
    evidence = {'results.json': file_sha(output / 'results.json')}
    for name in LEGACY_NAMES:
        folder = output / 'native' / name
        log = folder / 'run.log'
        row = verify_case(name,
                          read(folder / 'run.started.json'),
                          read(folder / 'run.finished.json'),
                          log.read_bytes(),
                          argv=invocation(repo, saved['python'], name),
                          cwd=harness,
                          log=log)
        require(saved['cases'][name] == row, 'legacy_replay_record_mismatch')
        cases[name] = row
        for suffix in ('log', 'started.json', 'finished.json'):
            path = folder / ('run.' + suffix)
            evidence[str(path.relative_to(output))] = file_sha(path)
    return {
        'schema': 'clocking-legacy-audit-v1',
        'head': head,
        'compiler_sha256': compiler['sha256'],
        'compiler_checkout_head': compiler['checkout_head'],
        'compiler_matches_run_head': compiler['checkout_head'] == head,
        'compiler_build_provenance': compiler['binary_to_commit_provenance'],
        'archive_manifest_sha256': saved['archive_manifest_sha256'],
        'original_selector_sha256': ORIGINAL_SELECTOR_SHA256,
        'original_groups': list(ORIGINAL_GROUPS),
        'original_selected_names': manifest['original_selected_names'],
        'original_selected_count': 438,
        'remaining_original_count': 436,
        'classification': CLASSIFICATION,
        'audit_verified': True,
        'semantic_pass': False,
        'original_criteria_pass': False,
        'raw_returncode': 1,
        'raw_returncode_scope': 'DERIVED_FROM_BOTH_OBSERVED_NATIVE_FAILURES',
        'counts': {
            'passed': 0,
            'failed': 2
        },
        'cases': cases,
        'evidence_sha256': sha(json.dumps(evidence, sort_keys=True).encode()),
        'global_status': 'HOLD'
    }


def core_fields(report):
    """Keep typed producer evidence bounded while preserving original red criteria."""
    require(
        report['schema'] == 'clocking-legacy-audit-v1'
        and report['original_selector_sha256'] == ORIGINAL_SELECTOR_SHA256
        and report['classification'] == CLASSIFICATION and report['audit_verified'] is True
        and report['semantic_pass'] is False and report['original_criteria_pass'] is False
        and type(report['raw_returncode']) is int and report['raw_returncode'] == 1
        and report['raw_returncode_scope'] == 'DERIVED_FROM_BOTH_OBSERVED_NATIVE_FAILURES'
        and exact_counts(report['counts'], 2) and report['global_status'] == 'HOLD',
        'legacy_core_status_changed')
    for key in ('head', 'compiler_checkout_head'):
        require(
            isinstance(report[key], str) and re.fullmatch(r'[0-9a-f]{40}', report[key]),
            'legacy_core_head_invalid')
    for key in ('compiler_sha256', 'archive_manifest_sha256', 'evidence_sha256'):
        require(
            isinstance(report[key], str) and re.fullmatch(r'[0-9a-f]{64}', report[key]),
            'legacy_core_hash_invalid')
    require(
        type(report['compiler_matches_run_head']) is bool and report['compiler_matches_run_head']
        == (report['head'] == report['compiler_checkout_head'])
        and report['compiler_build_provenance'] == 'NOT_INDEPENDENTLY_VERIFIED'
        and type(report['original_selected_count']) is int
        and report['original_selected_count'] == 438
        and type(report['remaining_original_count']) is int
        and report['remaining_original_count'] == 436, 'legacy_core_provenance_invalid')
    require(set(report['cases']) == set(LEGACY_NAMES), 'legacy_core_selection_changed')
    for row in report['cases'].values():
        require(
            row['summary_status'] == 'FAILED' and exact_counts(row['counts'], 1)
            and type(row['actual_exit']) is int and row['actual_exit'] == 10
            and type(row['raw_wait_status']) is int and row['raw_wait_status'] == 2560
            and row['semantic_pass'] is False and row['fingerprint_verified'] is True
            and isinstance(row['log_sha256'], str)
            and re.fullmatch(r'[0-9a-f]{64}', row['log_sha256']), 'legacy_core_case_changed')
    keys = ('schema', 'head', 'compiler_sha256', 'compiler_checkout_head',
            'compiler_matches_run_head', 'compiler_build_provenance', 'archive_manifest_sha256',
            'original_selector_sha256', 'original_selected_count', 'remaining_original_count',
            'classification', 'audit_verified', 'semantic_pass', 'original_criteria_pass',
            'raw_returncode', 'raw_returncode_scope', 'counts', 'cases', 'evidence_sha256',
            'global_status')
    return {key: report[key] for key in keys}


def exact_counts(counts, failed):
    """Booleans cannot stand in for integer evidence counters."""
    return (counts == {
        'passed': 0,
        'failed': failed
    } and all(type(value) is int for value in counts.values()))


def run(repo, compiler, output):  # pylint: disable=too-many-locals
    """Retain sequential native failures in an owned isolated harness directory."""
    repo, compiler = Path(repo).resolve(strict=True), Path(compiler).resolve(strict=True)
    manifest = verify_archive(repo)
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    harness = output / 'harness/test_regress'
    (harness / 't').mkdir(parents=True)
    for row in manifest['fixtures']:
        shutil.copy2(repo / ARCHIVE / row['archived_path'],
                     harness / 't' / Path(row['original_path']).name)
    for name in ('input.vc', 'Makefile'):
        shutil.copy2(repo / 'test_regress' / name, harness / name)
    before = source_inputs(repo)
    head = git_head(repo)
    built = compiler_inputs(compiler)
    env = os.environ.copy()
    for name in ('HARNESS_UPDATE_GOLDEN', 'TEST_REGRESS', 'VERILATOR_TESTS_SITE',
                 'VERILATOR_TESTS_OBJ_ROOT'):
        env.pop(name, None)
    env.update(VERILATOR_ROOT=built['root'], VERILATOR_BIN=str(compiler))
    cases = {}
    for name in LEGACY_NAMES:
        folder = output / 'native' / name
        argv = invocation(repo, sys.executable, name)
        subprocess.run([
            sys.executable,
            str(repo / 'ci/portable/native_process.py'), '--cwd',
            str(harness), '--out',
            str(folder), '--name', 'run', '--timeout', '900', '--min-disk-bytes', '536870912',
            '--', *argv
        ],
                       env=env,
                       check=False)
        log = folder / 'run.log'
        cases[name] = verify_case(name,
                                  read(folder / 'run.started.json'),
                                  read(folder / 'run.finished.json'),
                                  log.read_bytes(),
                                  argv=argv,
                                  cwd=harness,
                                  log=log)
    require(git_head(repo) == head, 'legacy_checkout_changed_during_replay')
    write(
        output / 'results.json', {
            'schema': 'clocking-legacy-replay-v1',
            'head': head,
            'python': sys.executable,
            'archive_manifest_sha256': file_sha(repo / ARCHIVE / 'manifest.json'),
            'source_inputs_before': before,
            'source_inputs_after': source_inputs(repo),
            'compiler_before': built,
            'compiler_after': compiler_inputs(compiler),
            'golden_updates': False,
            'cases': cases
        })
    report = audit(repo, output)
    write(output / 'audit.json', report)
    return report


def main():
    """Return audit status; raw legacy criteria remain recorded as failure."""
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='action', required=True)
    for action in ('run', 'audit'):
        command = subparsers.add_parser(action)
        command.add_argument('--repo', type=Path, required=True)
        command.add_argument('--output', type=Path, required=True)
        if action == 'run':
            command.add_argument('--compiler', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = run(args.repo, args.compiler, args.output) if args.action == 'run' else audit(
            args.repo, args.output)
        print(json.dumps(core_fields(report), sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        print('CLOCKING_LEGACY_AUDIT_FAILED: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
