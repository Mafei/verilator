#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
# pylint: disable=missing-function-docstring
"""Reject missing, altered and falsely green legacy evidence."""

import copy
import gzip
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import clocking_legacy as legacy

ROOT = Path(__file__).resolve().parents[2]


class ArchiveTest(unittest.TestCase):
    """The manifest cannot redefine the old fixtures or selector."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.archive = self.repo / legacy.ARCHIVE
        shutil.copytree(ROOT / legacy.ARCHIVE, self.archive)

    def manifest(self):
        return self.archive / 'manifest.json'

    def change_manifest(self, change):
        data = legacy.read(self.manifest())
        change(data)
        self.manifest().write_text(json.dumps(data))

    def test_exact_archive_and_original_order(self):
        data = legacy.verify_archive(self.repo)
        self.assertEqual(len(data['original_selected_names']), 438)
        self.assertEqual(tuple(data['original_groups']), legacy.ORIGINAL_GROUPS)
        self.assertEqual(legacy.selector_sha(data['original_selected_names']),
                         legacy.ORIGINAL_SELECTOR_SHA256)

    def test_coherent_fixture_and_manifest_edit_is_rejected(self):
        path = self.archive / 'fixtures/t_clocking_output_unsup.out'
        path.write_bytes(path.read_bytes().replace(b'Unsupported:', b'Other error:'))

        def update(data):
            row = next(row for row in data['fixtures'] if row['archived_path'].endswith('.out'))
            row['sha256'] = legacy.file_sha(path)
            row['bytes'] = path.stat().st_size

        self.change_manifest(update)
        with self.assertRaisesRegex(ValueError, 'archive_fixture_bytes_changed'):
            legacy.verify_archive(self.repo)

    def test_selection_and_consistent_rehash_cannot_drop_failures(self):

        def update(data):
            data['original_selected_names'].remove(legacy.LEGACY_NAMES[0])
            data['original_selector_sha256'] = legacy.selector_sha(data['original_selected_names'])

        self.change_manifest(update)
        with self.assertRaisesRegex(ValueError, 'original_selection_mismatch'):
            legacy.verify_archive(self.repo)

    def test_canonical_path_is_never_overlaid(self):
        path = self.repo / 'test_regress/t/t_clocking_output_iface.py'
        path.parent.mkdir(parents=True)
        path.symlink_to('/missing/owned-by-someone-else')
        with self.assertRaisesRegex(ValueError, 'canonical_legacy_path_present'):
            legacy.verify_archive(self.repo)
        self.assertTrue(path.is_symlink())

    def test_lost_executable_mode_and_missing_raw_log_are_rejected(self):
        path = self.archive / 'fixtures/t_clocking_output_iface.py'
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'archive_fixture_mode_changed'):
            legacy.verify_archive(self.repo)
        path.chmod(0o700)
        (self.archive / 'historical-427/clocking_output_iface/driver.log.gz').unlink()
        with self.assertRaises(FileNotFoundError):
            legacy.verify_archive(self.repo)

    def test_historical_raw_log_bytes_are_checked(self):
        path = self.archive / 'historical-427/clocking_output_iface/driver.log.gz'
        path.write_bytes(gzip.compress(gzip.decompress(path.read_bytes()) + b'changed\n', mtime=0))
        with self.assertRaisesRegex(ValueError, 'historical_bytes_changed'):
            legacy.verify_archive(self.repo)


class NativeFailureTest(unittest.TestCase):
    """Expected applicability never overrides the original native failure."""

    def setUp(self):
        self.name = legacy.LEGACY_NAMES[0]
        folder = ROOT / legacy.ARCHIVE / 'historical-427' / self.name
        self.started = legacy.read(folder / 'driver.started.json')
        self.receipt = legacy.read(folder / 'driver.finished.json')
        self.raw = gzip.decompress((folder / 'driver.log.gz').read_bytes())

    def verify(self):
        return legacy.verify_case(self.name, self.started, self.receipt, self.raw)

    def replace_log(self, old, new):
        self.raw = self.raw.replace(old, new)
        self.receipt.update(log_sha256=legacy.sha(self.raw), log_bytes=len(self.raw))

    def test_real_historical_wait4_failure_stays_red(self):
        row = self.verify()
        self.assertEqual(row['actual_exit'], 10)
        self.assertEqual(row['raw_wait_status'], 2560)
        self.assertEqual(row['counts'], {'passed': 0, 'failed': 1})
        self.assertIs(row['semantic_pass'], False)

    def test_log_and_receipt_mutations_are_rejected(self):
        original = copy.deepcopy(self.receipt)
        for change in ({
                'actual_exit': 0,
                'exit_status': 0,
                'raw_wait_status': 0
        }, {
                'termination_reason': 'timeout'
        }, {
                'kill_sent': True
        }, {
                'actual_exit': True
        }, {
                'wait4_pid': self.receipt['pid'] + 1
        }, {
                'log_sha256': '0' * 64
        }, {
                'exited_normally': False,
                'signal': 11,
                'exit_status': None,
                'actual_exit': -11,
                'raw_wait_status': 11
        }):
            with self.subTest(change=change):
                self.receipt = dict(original, **change)
                with self.assertRaises(ValueError):
                    self.verify()

    def test_same_exit_with_different_runtime_failure_is_rejected(self):
        self.replace_log(b'got=0 exp=3 (pattern_i.id !== expected.id)',
                         b'got=1 exp=3 (pattern_i.id !== expected.id)')
        with self.assertRaisesRegex(ValueError, 'legacy_failure_fingerprint_changed'):
            self.verify()

    def test_rehashed_green_counts_or_pass_marker_cannot_be_accepted(self):
        self.replace_log(b'Passed 0  Failed 1', b'Passed 1  Failed 0')
        with self.assertRaisesRegex(ValueError, 'legacy_raw_criteria_changed'):
            self.verify()

    def test_rehashed_duplicate_summary_is_rejected(self):
        self.raw += b'==TESTS DONE, FAILED: Passed 0  Failed 1  Time 0:01\n'
        self.receipt.update(log_sha256=legacy.sha(self.raw), log_bytes=len(self.raw))
        with self.assertRaisesRegex(ValueError, 'exactly one completed harness summary'):
            self.verify()

    def test_preserved_fingerprint_cannot_hide_an_unrelated_diagnostic(self):
        for name in legacy.LEGACY_NAMES:
            folder = ROOT / legacy.ARCHIVE / 'historical-427' / name
            self.name = name
            self.started = legacy.read(folder / 'driver.started.json')
            original = legacy.read(folder / 'driver.finished.json')
            raw = gzip.decompress((folder / 'driver.log.gz').read_bytes())
            for diagnostic in (b'%Error: unrelated failure\n',
                               b'%Error-UNSUPPORTED: unrelated boundary\n',
                               b'%Warning-BOGUS: an additional failure\n',
                               b'vlt/t_unrelated: FAILED: another failure\n',
                               b'g++: error: an unrelated compiler error\n',
                               b'make: *** [target] Error 1\n',
                               b'Traceback (most recent call last):\n'):
                with self.subTest(name=name, diagnostic=diagnostic):
                    self.raw = raw + diagnostic
                    self.receipt = dict(original,
                                        log_sha256=legacy.sha(self.raw),
                                        log_bytes=len(self.raw))
                    with self.assertRaisesRegex(ValueError, 'legacy_unknown_diagnostic'):
                        self.verify()


class CoreTest(unittest.TestCase):
    """A green audit cannot become semantic credit in typed core fields."""

    def setUp(self):
        self.report = {
            'schema': 'clocking-legacy-audit-v1',
            'head': legacy.BASE_SHA,
            'compiler_checkout_head': legacy.BASE_SHA,
            'compiler_sha256': 'a' * 64,
            'compiler_matches_run_head': True,
            'compiler_build_provenance': 'NOT_INDEPENDENTLY_VERIFIED',
            'archive_manifest_sha256': 'b' * 64,
            'evidence_sha256': 'c' * 64,
            'original_selector_sha256': legacy.ORIGINAL_SELECTOR_SHA256,
            'original_selected_count': 438,
            'remaining_original_count': 436,
            'classification': legacy.CLASSIFICATION,
            'audit_verified': True,
            'semantic_pass': False,
            'original_criteria_pass': False,
            'raw_returncode': 1,
            'raw_returncode_scope': 'DERIVED_FROM_BOTH_OBSERVED_NATIVE_FAILURES',
            'counts': {
                'passed': 0,
                'failed': 2
            },
            'global_status': 'HOLD',
            'cases': {}
        }
        for name in legacy.LEGACY_NAMES:
            folder = ROOT / legacy.ARCHIVE / 'historical-427' / name
            self.report['cases'][name] = legacy.verify_case(
                name, legacy.read(folder / 'driver.started.json'),
                legacy.read(folder / 'driver.finished.json'),
                gzip.decompress((folder / 'driver.log.gz').read_bytes()))

    def test_audit_success_preserves_original_failed_criteria(self):
        result = legacy.core_fields(self.report)
        self.assertTrue(result['audit_verified'])
        self.assertFalse(result['original_criteria_pass'])
        self.assertFalse(result['semantic_pass'])
        self.assertEqual(result['raw_returncode'], 1)

    def test_case_projection_drops_extra_nested_payload(self):
        row = self.report['cases'][legacy.LEGACY_NAMES[0]]
        original = copy.deepcopy(row)
        row['unbounded_payload'] = {'unexpected': 'x' * 10000}
        result = legacy.core_fields(self.report)
        self.assertEqual(result['cases'][legacy.LEGACY_NAMES[0]], original)
        self.assertIn('unbounded_payload', row)

    def test_status_count_identity_and_type_tampering(self):
        original = copy.deepcopy(self.report)
        for change in ({
                'semantic_pass': True
        }, {
                'original_criteria_pass': True
        }, {
                'classification': 'PASS'
        }, {
                'global_status': 'PASS'
        }, {
                'raw_returncode': 0
        }, {
                'raw_returncode': True
        }, {
                'counts': {
                    'passed': False,
                    'failed': 2
                }
        }, {
                'compiler_matches_run_head': False
        }, {
                'original_selected_count': 436
        }, {
                'original_selector_sha256': '0' * 64
        }):
            with self.subTest(change=change):
                self.report = dict(original, **change)
                with self.assertRaises(ValueError):
                    legacy.core_fields(self.report)
        self.report = original
        self.report['cases'][legacy.LEGACY_NAMES[0]]['semantic_pass'] = True
        with self.assertRaisesRegex(ValueError, 'legacy_core_case_changed'):
            legacy.core_fields(self.report)


if __name__ == '__main__':
    unittest.main()
