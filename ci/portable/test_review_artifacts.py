#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Synthetic artifact corruption controls; no compiler, model or container runs."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock
import tarfile

import log_evidence
import review_artifacts as review
from run_regressions import GROUPS


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class ArtifactsTest(unittest.TestCase):
    """Exercise real count/AST/package/receipt validation with isolated fixtures."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.head = 'a' * 40
        self.args = SimpleNamespace(expected_head=self.head,
                                    run_id=123,
                                    output=self.root / 'review.json')
        self.needs = {'mac': 'success', 'rocky': 'success'}
        self.missing_output = False
        self.compiler = {}
        self.case122_reports = {}
        for name, platform in [('mac', 'macos-arm64'), ('rocky', 'rocky8-x86_64')]:
            main = self.root / (name + '-main')
            (main / 'out').mkdir(parents=True)
            (main / 'logs').mkdir()
            for relative in ('ci/portable/smoke.py', 'test_regress/vltest_generated_ids.py',
                             'test_regress/t/t_debug_emitv.out'):
                destination = main / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((review.ROOT / relative).read_bytes())
            (main / 'out/provenance.txt').write_text(self.head + '\n')
            rows = {}
            for group, names in GROUPS.items():
                text = ''.join('vlt/t_' + n + ': Self PASSED\n' for n in names)
                text += '==TESTS DONE, PASSED: Passed %d  Failed 0  Time 0:01\n' % len(names)
                (main / 'logs' / (group + '-regressions.log')).write_text(text)
                rows[group] = dict(commit=self.head,
                                   selected=names,
                                   expected=len(names),
                                   returncode=0,
                                   success=True,
                                   counts={
                                       'passed': len(names),
                                       'failed': 0
                                   },
                                   summary_status='PASSED')
            write_json(main / 'out/regression-results.json', rows)
            ast = main / 'test_regress/obj_vlt/t_debug_emitv/Vfixture_width.tree.v'
            ast.parent.mkdir(parents=True)
            ast.write_bytes((review.ROOT / 'test_regress/t/t_debug_emitv.out').read_bytes())
            write_json(main / 'out/enum-hash-evidence.json',
                       [log_evidence.enum_evidence(ast, main)])
            if name == 'mac':
                binary = struct.pack('<8I', 0xFEEDFACF, 0x0100000C, 0, 2, 0, 0, 0, 0)
            else:
                binary = bytearray(32)
                binary[:6] = b'\x7fELF\x02\x01'
                binary[18:20] = struct.pack('<H', 62)
                binary = bytes(binary)
            self.compiler[name] = binary
            self.bundle(name, platform, binary)
            write_json(
                main / 'out/icarus/check-full18.json', {
                    'compiler_head': self.head,
                    'full18_gate_exit': 0,
                    'selected': 18,
                    'counts': {
                        'passed': 18
                    }
                })
            write_json(
                main / 'out/finish9/check.json', {
                    'commit': self.head,
                    'strict_gate_exit': 0,
                    'selected': 9,
                    'executed': 9,
                    'passed': 9,
                    'failed': 0
                })
            write_json(
                main / 'pinned-icarus/RUN_SUMMARY.json', {
                    'verilator_head': self.head,
                    'pin': review.PIN,
                    'overall_exit': 1,
                    'fixed_selected': 128,
                    'default_denominator': 3850,
                    'pair_status_counts': {
                        'PASS_BOTH': 127,
                        'UNREVIEWED_OUTPUT_DIFFERENCE': 1
                    },
                    'unselected_UNRUN': 3722,
                    'full_suite_complete': False
                })
            # Synthetic only: case122 retains its original oracle failure.
            case122 = {
                'head': self.head,
                'scenario_id': review.queue_review.SID,
                'reviewed_classification': 'REFERENCE_STANDARD_CONFLICT',
                'original_pair_status': 'UNREVIEWED_OUTPUT_DIFFERENCE',
                'original_source_sha256': review.queue_review.SOURCE_SHA,
                'original_oracle_sha256': review.queue_review.ORACLE_SHA,
                'verilator_compiler_sha256': hashlib.sha256(binary).hexdigest(),
                'raw_pair_status_counts': {
                    'PASS_BOTH': 127,
                    'UNREVIEWED_OUTPUT_DIFFERENCE': 1
                },
                'raw_output_difference_count': 1,
                'reviewed_case_count': 1,
                'standard': {
                    'status': 'PASS',
                    'checks_per_profile': 100,
                    'profiles': ['two', 'four'],
                    'raw_wait_status': 'NOT_RECORDED',
                    'scope': 'harness_checked_return_and_assertions',
                    'source_sha256': 'a' * 64,
                    'driver_sha256': 'b' * 64,
                    'logs_sha256': ['c' * 64, 'd' * 64]
                },
                'semantic_gate_unchanged': True,
                'overall_acceptance': False,
                'review_gate_exit': 0
            }
            self.case122_reports[str(main)] = case122
            write_json(main / 'out/case122-review.json', case122)
        self.migration()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(review, 'git_head', return_value=self.head))
        self.stack.enter_context(
            mock.patch.object(review.queue_review,
                              'collect',
                              side_effect=lambda main, *_args: self.case122_reports[str(main)]))
        self.stack.enter_context(
            mock.patch.object(review.check_results.subprocess,
                              'check_output',
                              return_value=self.head))
        # Separate tests cover native byte bindings; these fixtures isolate the
        # orchestration, original regression checker, normalizer and tar readers.
        self.stack.enter_context(
            mock.patch.object(review,
                              'thread_evidence',
                              side_effect=lambda main, *_args: ({
                                  'passed_names':
                                  6,
                                  'counts': {
                                      'passed': 6,
                                      'failed': 0
                                  },
                                  'native_exit':
                                  0,
                                  'waves': [{
                                      'profile': profile,
                                      'histories': 3,
                                      'records': records,
                                      'sha256': 'a' * 64
                                  }
                                            for profile, records in [('two_state', 25),
                                                                     ('four_state', 26)]]
                              }, '/work' if main.name == 'rocky-main' else str(main), False)))
        self.stack.enter_context(
            mock.patch.object(review,
                              'ram_evidence',
                              return_value=({
                                  'assertions': 318,
                                  'reports': 84,
                                  'histories': 30,
                                  'records': 228,
                                  'wave_sha256': 'a' * 64
                              }, False)))

    def bundle(self, name, platform, binary, update_compiler=True):
        main = self.root / (name + '-main')
        archive = main / 'out' / ('verilator-fourstate-' + platform + '.tar.gz')
        with tarfile.open(archive, 'w:gz') as bundle:
            for member, data in [('bin/verilator_bin', binary),
                                 ('provenance.txt', (self.head + '\n').encode())]:
                info = tarfile.TarInfo('verilator-fourstate/' + member)
                info.size = len(data)
                bundle.addfile(info, io.BytesIO(data))
        (main / 'out/SHA256SUMS').write_text(review.sha(archive) + '  ' + archive.name + '\n')
        if update_compiler:
            (main / 'out/compiler-SHA256SUMS'
             ).write_text(hashlib.sha256(binary).hexdigest() + '  bin/verilator_bin\n')

    def migration(self, status=0):
        main = self.root / 'mac-main'
        write_json(
            main / 'out/migration-smoke.json', {
                'schema':
                'portable-migration-return-v1',
                'head':
                self.head,
                'run_id':
                123,
                'run_attempt':
                int(os.environ.get('GITHUB_RUN_ATTEMPT', '1')),
                'job':
                'macos',
                'platform':
                'macos-arm64',
                'completed':
                True,
                'shell_returned_status':
                status,
                'raw_wait_status':
                'NOT_RECORDED',
                'command': [
                    'python3', 'ci/portable/smoke.py',
                    '/tmp/verilator-relocated/verilator-fourstate/bin/verilator',
                    '/tmp/portable-smoke'
                ],
                'script_sha256':
                review.sha(review.ROOT / 'ci/portable/smoke.py'),
                'package_sha256':
                review.sha(main / 'out/verilator-fourstate-macos-arm64.tar.gz'),
                'relocated_compiler_sha256':
                hashlib.sha256(self.compiler['mac']).hexdigest()
            })

    def producer_records(self):
        result = {}
        for name, platform in [('mac', 'macos-arm64'), ('rocky', 'rocky8-x86_64')]:
            main = self.root / (name + '-main')
            args = SimpleNamespace(expected_head=self.head,
                                   run_id=123,
                                   output=main / 'out/producer-core-review.json',
                                   platform=platform,
                                   prior_result=self.needs[name],
                                   producer_root='/work' if name == 'rocky' else str(main))
            output = self.root / (name + '-github-output')
            output.write_text('')
            with mock.patch.object(review, 'ROOT', main), mock.patch.dict(
                    os.environ,
                    GITHUB_OUTPUT=str(output)), contextlib.redirect_stdout(io.StringIO()):
                actual = review.producer(args)
            result[name] = json.loads(args.output.read_text())
            self.assertEqual(actual, result[name]['actual_exit'])
            lines = output.read_text().splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0].removeprefix('core_review=')), result[name])
        return result

    def relay(self, records, expected):
        environment = {
            'MACOS_JOB_RESULT': self.needs['mac'],
            'ROCKY8_JOB_RESULT': self.needs['rocky'],
            'MACOS_CORE_REVIEW': '' if self.missing_output else json.dumps(records['mac']),
            'ROCKY8_CORE_REVIEW': json.dumps(records['rocky'])
        }
        with mock.patch.dict(os.environ, environment), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.summarize(self.args), expected)
        return json.loads(self.args.output.read_text())

    def execute(self, expected):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.relay(self.producer_records(), expected)

    def test_consistent_synthetic_core(self):
        row = self.execute(1)
        self.assertTrue(row['audit_integrity'])
        self.assertEqual(row['artifact_zip_transport_digest'], 'NOT_INDEPENDENTLY_VERIFIED')

    def set_regression(self, group, counts, status, code):
        """Create a real harness log and matching producer record for one group."""
        labels = {
            'passed': 'Passed',
            'failed': 'Failed',
            'failed-first': 'Failed-First',
            'skipped': 'Skipped',
            'left': 'Left',
            'running': 'Running'
        }
        for name in ('mac', 'rocky'):
            main = self.root / (name + '-main')
            path = main / 'out/regression-results.json'
            rows = json.loads(path.read_text())
            selected = GROUPS[group]
            text = ''.join('vlt/t_' + n + ': Self PASSED\n' for n in selected[:counts['passed']])
            text += '==TESTS DONE, ' + status + ': ' + '  '.join(
                labels[key] + ' ' + str(value) for key, value in counts.items()) + '  Time 0:01\n'
            (main / 'logs' / (group + '-regressions.log')).write_text(text)
            rows[group].update(counts=counts,
                               summary_status=status,
                               returncode=code,
                               success=code == 0
                               and review.passed_counts(status, counts, len(selected))
                               and review.passed_names(text, selected))
            write_json(path, rows)

    def test_regression_counters_cover_all_selected_groups(self):
        row = self.execute(1)
        self.assertTrue(row['audit_integrity'])
        for platform in row['platforms'].values():
            data = platform['regressions']
            self.assertEqual(set(data['by_group']), set(GROUPS))
            self.assertEqual(data['totals']['passed'], sum(map(len, GROUPS.values())))
            self.assertTrue(
                all(value == 0 for key, value in data['totals'].items() if key != 'passed'))
            self.assertEqual(data['failed_groups'], [])

    def test_regression_failure_retains_complete_totals_and_nonzero_gate(self):
        group = next(iter(GROUPS))
        self.set_regression(group, {'passed': len(GROUPS[group]) - 1, 'failed': 1}, 'FAILED', 10)
        row = self.execute(1)
        self.assertTrue(row['audit_integrity'])
        for platform in row['platforms'].values():
            data = platform['regressions']
            self.assertEqual(data['totals']['passed'], sum(map(len, GROUPS.values())) - 1)
            self.assertEqual(data['totals']['failed'], 1)
            self.assertEqual(data['failed_groups'], [group])
            self.assertEqual(data['by_group'][group]['returncode'], 10)
            self.assertFalse(data['by_group'][group]['success'])

    def test_regression_pass_counts_do_not_hide_nonzero_return(self):
        group = next(iter(GROUPS))
        for code in (7, -9):
            with self.subTest(code=code):
                self.set_regression(group, {
                    'passed': len(GROUPS[group]),
                    'failed': 0
                }, 'PASSED', code)
                row = self.execute(1)
                self.assertTrue(row['audit_integrity'])
                data = row['platforms']['macos-arm64']['regressions']
                self.assertEqual(data['totals']['passed'], sum(map(len, GROUPS.values())))
                self.assertEqual(data['failed_groups'], [group])
                self.assertEqual(data['by_group'][group]['returncode'], code)
                self.assertTrue(data['by_group'][group]['passed_names_match'])
                self.assertFalse(data['by_group'][group]['success'])

    def test_regression_retry_skip_and_unfinished_counts_stay_separate(self):
        group = next(iter(GROUPS))
        for counter in ('failed-first', 'skipped', 'left', 'running'):
            with self.subTest(counter=counter):
                passed = len(GROUPS[group]) - int(counter != 'failed-first')
                counts = {'passed': passed, 'failed': 0, counter: 1}
                status = 'PASSED w/SKIPS' if counter == 'skipped' else 'PASSED'
                self.set_regression(group, counts, status, 0)
                row = self.execute(1)
                self.assertTrue(row['audit_integrity'])
                data = row['platforms']['macos-arm64']['regressions']
                self.assertEqual(data['totals'][counter], 1)
                self.assertEqual(data['totals']['passed'],
                                 sum(map(len, GROUPS.values())) - int(counter != 'failed-first'))
                self.assertEqual(data['failed_groups'], [group])
                self.assertFalse(data['by_group'][group]['success'])

    def test_regression_relay_rejects_tampered_totals_types_and_groups(self):
        original = self.producer_records()
        group = next(iter(GROUPS))
        changes = [
            (('totals', 'passed'), True),
            (('totals', 'passed'), sum(map(len, GROUPS.values())) + 1),
            (('failed_groups', ), [group]),
            (('by_group', 'unexpected_group'), {}),
            (('by_group', group, 'counts', 'failed'), False),
            (('by_group', group, 'counts', 'passed'), -1),
            (('by_group', group, 'counts', 'unknown'), 0),
            (('by_group', group, 'returncode'), True),
            (('by_group', group, 'returncode'), 7),
            (('by_group', group, 'passed_names_match'), 1),
            (('by_group', group, 'summary_status'), 'UNTRUSTED_STATUS'),
        ]
        for path, value in changes:
            with self.subTest(path=path, value=value):
                rows = json.loads(json.dumps(original))
                target = rows['mac']['core']['regressions']
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.assertFalse(self.relay(rows, 2)['audit_integrity'])

    def test_regression_log_and_record_mismatch_is_not_relayed(self):
        path = self.root / 'mac-main/out/regression-results.json'
        rows = json.loads(path.read_text())
        rows[next(iter(GROUPS))]['counts']['passed'] -= 1
        write_json(path, rows)
        row = self.execute(2)
        self.assertFalse(row['audit_integrity'])
        self.assertNotIn('regressions', row['platforms']['macos-arm64'])

    def test_case122_standard_pass_keeps_original_failure(self):
        result = self.execute(1)
        case122 = result['platforms']['macos-arm64']['case122_review']
        self.assertEqual(case122['standard']['status'], 'PASS')
        self.assertEqual(case122['original_pair_status'], 'UNREVIEWED_OUTPUT_DIFFERENCE')
        self.assertEqual(case122['reviewed_case_count'], 1)
        self.assertFalse(case122['overall_acceptance'])

    def test_case122_changed_saved_report_is_rejected(self):
        path = self.root / 'mac-main/out/case122-review.json'
        data = json.loads(path.read_text())
        data['standard']['status'] = 'FAIL'
        write_json(path, data)
        self.assertFalse(self.execute(2)['audit_integrity'])

    def test_case122_relay_rejects_broadened_or_green_classification(self):
        original = self.producer_records()
        for change in [{
                'scenario_id': 'another-case'
        }, {
                'original_pair_status': 'PASS_BOTH'
        }, {
                'reviewed_case_count': 2
        }, {
                'raw_output_difference_count': 0
        }, {
                'standard':
                dict(original['mac']['core']['case122_review']['standard'], status='FAIL')
        }]:
            rows = json.loads(json.dumps(original))
            rows['mac']['core']['case122_review'].update(change)
            self.assertFalse(self.relay(rows, 2)['audit_integrity'])

    def test_case122_cannot_mix_same_head_platform_compilers(self):
        rows = self.producer_records()
        rows['mac']['core']['case122_review']['verilator_compiler_sha256'] = (
            rows['rocky']['core']['case122_review']['verilator_compiler_sha256'])
        self.assertFalse(self.relay(rows, 2)['audit_integrity'])

    def test_case122_producer_compiler_must_match_package(self):
        case = self.case122_reports[str(self.root / 'mac-main')]
        case['verilator_compiler_sha256'] = 'e' * 64
        write_json(self.root / 'mac-main/out/case122-review.json', case)
        self.assertFalse(self.execute(2)['audit_integrity'])

    def test_original_needs_failure_stays_semantic_one(self):
        self.needs['mac'] = 'failure'
        self.assertTrue(self.execute(1)['audit_integrity'])

    def test_original_reported_gate_failure_stays_one(self):
        path = self.root / 'mac-main/pinned-icarus/RUN_SUMMARY.json'
        row = json.loads(path.read_text())
        row['overall_exit'] = 1
        write_json(path, row)
        self.assertTrue(self.execute(1)['audit_integrity'])

    def test_migration_seven_and_shell143_are_not_raw_signal(self):
        for status in (7, 143):
            with self.subTest(status=status):
                self.migration(status)
                row = self.execute(1)
                self.assertTrue(row['audit_integrity'])
                self.assertEqual(row['platforms']['macos-arm64']['migration']['raw_wait_status'],
                                 'NOT_RECORDED')

    def test_missing_or_wrong_migration_record_is_two(self):
        path = self.root / 'mac-main/out/migration-smoke.json'
        original = json.loads(path.read_text())
        for change in (None, {
                'head': 'b' * 40
        }, {
                'run_id': 999
        }, {
                'shell_returned_status': False
        }, {
                'completed': False
        }):
            with self.subTest(change=change):
                path.unlink(missing_ok=True)
                if change is not None:
                    write_json(path, dict(original, **change))
                self.assertFalse(self.execute(2)['audit_integrity'])

    def test_wrong_provenance_and_missing_group(self):
        path = self.root / 'mac-main/out/provenance.txt'
        path.write_text('b' * 40 + '\n')
        self.execute(2)
        path.write_text(self.head + '\n')
        path = self.root / 'mac-main/out/regression-results.json'
        rows = json.loads(path.read_text())
        rows.pop(next(iter(rows)))
        write_json(path, rows)
        self.execute(2)

    def test_consistent_ast_manifest_cannot_replace_original_gold(self):
        main = self.root / 'mac-main'
        path = main / 'test_regress/obj_vlt/t_debug_emitv/Vfixture_width.tree.v'
        path.write_bytes(path.read_bytes() + b'// Changed public AST literal\n')
        write_json(main / 'out/enum-hash-evidence.json', [log_evidence.enum_evidence(path, main)])
        self.execute(2)

    def test_tar_compiler_and_architecture_mismatch(self):
        self.bundle('mac', 'macos-arm64', self.compiler['mac'] + b'changed', update_compiler=False)
        self.execute(2)
        wrong = struct.pack('<8I', 0xFEEDFACF, 0x01000007, 0, 2, 0, 0, 0, 0)
        self.bundle('mac', 'macos-arm64', wrong)
        self.execute(2)

    def test_missing_producer_output_does_not_become_green(self):
        self.missing_output = True
        self.execute(2)

    def test_reported_counts_and_false_complete_are_not_hardcoded(self):
        path = self.root / 'mac-main/pinned-icarus/RUN_SUMMARY.json'
        record = json.loads(path.read_text())
        record.update(overall_exit=1,
                      pair_status_counts={
                          'PASS_BOTH': 103,
                          'UNREVIEWED_OUTPUT_DIFFERENCE': 3,
                          'VERILATOR_COMPILE_FAILED': 10,
                          'VERILATOR_UNSUPPORTED': 12
                      })
        write_json(path, record)
        case122 = self.case122_reports[str(self.root / 'mac-main')]
        case122['raw_pair_status_counts'] = record['pair_status_counts']
        case122['raw_output_difference_count'] = 3
        write_json(self.root / 'mac-main/out/case122-review.json', case122)
        row = self.execute(1)['platforms']['macos-arm64']['other_gates']['fixed128']
        self.assertEqual(row['pair_status_counts'], record['pair_status_counts'])
        self.assertEqual(row['unselected_UNRUN'], 3722)
        self.assertIs(row['full_suite_complete'], False)

    def test_reported_complete_cannot_hide_remaining_unrun(self):
        path = self.root / 'mac-main/pinned-icarus/RUN_SUMMARY.json'
        record = json.loads(path.read_text())
        record['full_suite_complete'] = True
        write_json(path, record)
        self.assertFalse(self.execute(2)['audit_integrity'])

    def test_relay_rejects_wrong_identity_status_types_and_counts(self):
        original = self.producer_records()
        for field, value in [('head', 'b' * 40), ('run_id', 999), ('run_attempt', 999),
                             ('audit_integrity', 1), ('actual_exit', False)]:
            with self.subTest(field=field):
                rows = json.loads(json.dumps(original))
                rows['mac'][field] = value
                self.assertFalse(self.relay(rows, 2)['audit_integrity'])
        rows = json.loads(json.dumps(original))
        rows['mac']['core']['selected_drivers'] = False
        self.relay(rows, 2)
        rows = json.loads(json.dumps(original))
        rows['rocky']['core']['ram']['assertions'] = 1
        self.relay(rows, 2)
        rows = json.loads(json.dumps(original))
        rows['mac']['core']['other_gates']['fixed128']['full_suite_complete'] = True
        self.relay(rows, 2)

    def test_late_upload_failure_and_ast_mismatch_remain_visible(self):
        rows = self.producer_records()
        self.needs['mac'] = 'failure'
        self.assertTrue(self.relay(rows, 1)['audit_integrity'])
        self.needs['mac'] = 'success'
        rows['mac']['core']['public_ast'][0]['normalized_sha256'] = 'b' * 64
        self.assertFalse(self.relay(rows, 2)['audit_integrity'])

    def test_relay_whitelists_fields_and_records_before_upload_scope(self):
        rows = self.producer_records()
        rows['mac']['raw_log'] = 'DO_NOT_RELAY_UNSCREENED_LOG'
        rows['mac']['core']['raw_log'] = 'DO_NOT_RELAY_UNSCREENED_LOG'
        row = self.relay(rows, 1)
        self.assertNotIn('DO_NOT_RELAY_UNSCREENED_LOG', json.dumps(row))
        self.assertEqual(row['verification_scope'], 'PRODUCER_FILES_RECOMPUTED_BEFORE_UPLOAD')
        self.assertIs(row['artifact_bytes_independently_recomputed_after_upload'], False)

    def test_explicit_recorded_root_mapping_is_required(self):
        rows = self.producer_records()
        rows['rocky']['file_mapping']['recorded_root'] = '/different'
        self.relay(rows, 2)
        with mock.patch.object(review, 'thread_evidence', return_value=({}, '/different', False)):
            self.execute(2)

    def test_native_output_file_failure_reaches_cli_exit_two(self):
        main = self.root / 'mac-main'
        argv = [
            'review_artifacts.py', 'producer', '--expected-head', self.head, '--run-id', '123',
            '--output',
            str(main / 'out/failed-output-review.json'), '--platform', 'macos-arm64',
            '--producer-root',
            str(main), '--prior-result', 'success'
        ]
        with mock.patch.object(review, 'ROOT', main), mock.patch.object(review.sys, 'argv', argv), \
                mock.patch.dict(os.environ, GITHUB_OUTPUT=str(self.root)), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.main(), 2)


class ReceiptTest(unittest.TestCase):
    """Bind actual file bytes to typed native records without launching a child."""

    def test_native_log_tamper_and_boolean_status(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            log = folder / 'run.log'
            log.write_text('fixture native stdout\n')
            start = {
                'schema': 'native-process-wait4-v1',
                'pid': 123,
                'log': '/original/out/thread-controls/run.log',
                'cwd': '/original/test_regress'
            }
            finish = dict(start,
                          wait4_pid=123,
                          actual_exit=0,
                          raw_wait_status=0,
                          log_sha256=review.sha(log),
                          log_bytes=log.stat().st_size,
                          exited_normally=True,
                          exit_status=0,
                          signal=None,
                          termination_reason=None,
                          kill_sent=False)
            write_json(folder / 'run.started.json', start)
            write_json(folder / 'run.finished.json', finish)
            review.native(folder, 'run', '/original', 'out/thread-controls/run.log',
                          'test_regress')
            log.write_text('tampered\n')
            with self.assertRaises(ValueError):
                review.native(folder, 'run', '/original', 'out/thread-controls/run.log',
                              'test_regress')
            log.write_text('fixture native stdout\n')
            for changed in ({
                    'actual_exit': False
            }, {
                    'exited_normally': False
            }, {
                    'signal': 6
            }, {
                    'exit_status': 1
            }, {
                    'kill_sent': True
            }):
                with self.subTest(changed=changed):
                    write_json(folder / 'run.finished.json', dict(finish, **changed))
                    with self.assertRaises(ValueError):
                        review.native(folder, 'run', '/original', 'out/thread-controls/run.log',
                                      'test_regress')

    def test_ram_timeout_reason_cannot_pass_with_zero_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            directory = root / 'out/ram-matrix/original'
            directory.mkdir(parents=True)
            functions = review.runpy.run_path(review.ROOT /
                                              'ci/portable/ram-matrix-original/verify_matrix.py')
            expected = functions['expected_histories']()
            actual = {key: value['changes'] for key, value in expected.items()}
            write_json(
                directory / 'oracle.json',
                dict(label='a' * 40,
                     assertions_total=318,
                     phase_reports=84,
                     complete_signal_histories=30,
                     complete_history_records=228,
                     expected_histories=expected,
                     actual_histories=actual))
            lines = []
            for width, up, packup in functions['LANES'].values():
                for phase in range(14):
                    value = functions['report_expected'](width, phase)
                    lines.append(
                        'ARRAY_TMP W=%d UP=%d PACKUP=%d phase=%d first=%s middle=%s last=%s side=%d checks=%d'
                        % (width, up, packup, phase, *value['words'], value['side_effects'],
                           value['checks']))
            (directory / 'run.log').write_text('\n'.join(lines) + '\n*-* All Finished *-*\n')
            (directory /
             't_fourstate_array_tmp.vcd').write_text('fixture wave; parser separately reused')
            functions['parse_vcd'] = lambda *_args: actual
            timed_out_zero = dict(actual_exit=0,
                                  termination_reason='timeout',
                                  kill_sent=False,
                                  exited_normally=True)
            with mock.patch.object(review.runpy, 'run_path',
                                   return_value=functions), mock.patch.object(
                                       review, 'native', return_value=timed_out_zero):
                _data, failed = review.ram_evidence(root, review.ROOT, 'a' * 40, '/original')
                self.assertTrue(failed)

    def test_thread_return_and_success_bind_native_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'out/thread-controls'
            folder.mkdir(parents=True)
            names = ['t_' + name for name in review.NAMES]
            text = ''.join('vltmt/' + name + ': Self PASSED\n' for name in names)
            text += '==TESTS DONE, PASSED: Passed 6  Failed 0  Time 0:01\n'
            (folder / 'run.log').write_text(text)
            base = dict(commit='a' * 40,
                        selected=list(review.NAMES),
                        actual_pass_names=names,
                        counts={
                            'passed': 6,
                            'failed': 0
                        },
                        summary_status='PASSED',
                        returncode=0,
                        success=True)
            record = dict(log='/original/out/thread-controls/run.log',
                          actual_exit=0,
                          termination_reason=None,
                          kill_sent=False,
                          exited_normally=True)
            write_json(folder / 'run.finished.json', record)
            for profile in ('two_state', 'four_state'):
                wave = root / 'test_regress/obj_vltmt/t_fourstate_mt_trace' / profile / 'simx.vcd'
                wave.parent.mkdir(parents=True)
                wave.write_text('fixture; actual oracle exercised by read-only historical data')
            functions = {
                'verify': lambda *_args: {
                    'complete_histories': 3,
                    'complete_records': 25
                }
            }
            with mock.patch.object(review, 'native',
                                   return_value=record), mock.patch.object(review.runpy,
                                                                           'run_path',
                                                                           return_value=functions):
                write_json(folder / 'results.json', base)
                self.assertFalse(review.thread_evidence(root, review.ROOT, 'a' * 40)[2])
                for change in ({'returncode': 1}, {'returncode': False}, {'success': False}):
                    with self.subTest(change=change):
                        write_json(folder / 'results.json', dict(base, **change))
                        with self.assertRaisesRegex(ValueError, 'thread_return_mismatch'):
                            review.thread_evidence(root, review.ROOT, 'a' * 40)
                for actual, returned, normal in ((7, 7, True), (-15, 143, False)):
                    record.update(actual_exit=actual, exited_normally=normal)
                    write_json(folder / 'results.json',
                               dict(base, returncode=returned, success=False))
                    self.assertTrue(review.thread_evidence(root, review.ROOT, 'a' * 40)[2])
                # Even a raced zero exit remains failed after the timeout guard fired.
                record.update(actual_exit=0, exited_normally=True, termination_reason='timeout')
                write_json(folder / 'results.json', base)
                self.assertTrue(review.thread_evidence(root, review.ROOT, 'a' * 40)[2])

    def test_migration_writer_failure_leaves_no_success_record(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'out').mkdir()
            (root / 'ci/portable').mkdir(parents=True)
            (root / 'ci/portable/smoke.py').write_text('# fixture only\n')
            binary = root / 'binary'
            binary.write_bytes(b'fixture only')
            args = SimpleNamespace(returned_status=7, package=binary, relocated_compiler=binary)
            with mock.patch.object(review, 'ROOT', root), mock.patch.object(
                    review, 'git_head',
                    return_value='a' * 40), mock.patch.dict(os.environ,
                                                            GITHUB_RUN_ID='123',
                                                            GITHUB_JOB='macos'):
                with mock.patch.object(Path,
                                       'rename',
                                       side_effect=OSError('fixture write failure')):
                    with self.assertRaises(OSError):
                        review.record_migration(args)
                self.assertFalse((root / 'out/migration-smoke.json').exists())
                self.assertFalse((root / 'out/migration-smoke.json.tmp').exists())
                review.record_migration(args)
                saved = json.loads((root / 'out/migration-smoke.json').read_text())
                self.assertEqual(saved['shell_returned_status'], 7)
                self.assertEqual(saved['raw_wait_status'], 'NOT_RECORDED')


if __name__ == '__main__':
    unittest.main()
