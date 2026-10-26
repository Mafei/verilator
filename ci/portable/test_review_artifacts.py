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
                                    artifacts=self.root,
                                    output=self.root / 'review.json',
                                    macos_result='success',
                                    rocky8_result='success',
                                    downloads_ok='true')
        self.compiler = {}
        for name, platform in [('mac', 'macos-arm64'), ('rocky', 'rocky8-x86_64')]:
            main = self.root / (name + '-main')
            (main / 'out').mkdir(parents=True)
            (main / 'logs').mkdir()
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
                self.root / (name + '-pair/RUN_SUMMARY.json'), {
                    'verilator_head': self.head,
                    'pin': review.PIN,
                    'overall_exit': 0,
                    'fixed_selected': 128,
                    'default_denominator': 3850,
                    'pair_status_counts': {
                        'PASS_BOTH': 128
                    },
                    'unselected_UNRUN': 3722,
                    'full_suite_complete': False
                })
        self.migration()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(review, 'git_head', return_value=self.head))
        self.stack.enter_context(
            mock.patch.object(review.check_results.subprocess,
                              'check_output',
                              return_value=self.head))
        # Separate tests cover native byte bindings; these fixtures isolate the
        # orchestration, original regression checker, normalizer and tar readers.
        self.stack.enter_context(
            mock.patch.object(review,
                              'thread_evidence',
                              return_value=({
                                  'scope': 'fixture_only'
                              }, '/fixture/producer', False)))
        self.stack.enter_context(
            mock.patch.object(review,
                              'ram_evidence',
                              return_value=({
                                  'scope': 'fixture_only'
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

    def execute(self, expected):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(review.review(self.args), expected)
        return json.loads(self.args.output.read_text())

    def test_consistent_synthetic_core(self):
        row = self.execute(0)
        self.assertTrue(row['audit_integrity'])
        self.assertEqual(row['artifact_zip_transport_digest'], 'NOT_INDEPENDENTLY_VERIFIED')

    def test_original_needs_failure_stays_semantic_one(self):
        self.args.macos_result = 'failure'
        self.assertTrue(self.execute(1)['audit_integrity'])

    def test_original_reported_gate_failure_stays_one(self):
        path = self.root / 'mac-pair/RUN_SUMMARY.json'
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

    def test_download_failure_does_not_become_green(self):
        self.args.downloads_ok = 'false'
        self.execute(2)

    def test_reported_counts_and_false_complete_are_not_hardcoded(self):
        path = self.root / 'mac-pair/RUN_SUMMARY.json'
        record = json.loads(path.read_text())
        record.update(overall_exit=1,
                      pair_status_counts={
                          'PASS_BOTH': 103,
                          'UNREVIEWED_OUTPUT_DIFFERENCE': 3,
                          'VERILATOR_COMPILE_FAILED': 10,
                          'VERILATOR_UNSUPPORTED': 12
                      })
        write_json(path, record)
        row = self.execute(1)['platforms']['macos-arm64']['other_gates']['fixed128']
        self.assertEqual(row['pair_status_counts'], record['pair_status_counts'])
        self.assertEqual(row['unselected_UNRUN'], 3722)
        self.assertIs(row['full_suite_complete'], False)

    def test_reported_complete_cannot_hide_remaining_unrun(self):
        path = self.root / 'mac-pair/RUN_SUMMARY.json'
        record = json.loads(path.read_text())
        record['full_suite_complete'] = True
        write_json(path, record)
        self.assertFalse(self.execute(2)['audit_integrity'])


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
