#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Keep revised applicability separate from the failed original clocking criteria."""
# pylint: disable=missing-function-docstring
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import check_results
import clocking_legacy
import review_artifacts as review
from run_regressions import GROUPS, actual_passed_names, selection_revision


def legacy_report(head, compiler_sha):
    """Synthetic native failures; actual fingerprint validation has separate controls."""
    return {
        'schema': 'clocking-legacy-audit-v1',
        'head': head,
        'compiler_sha256': compiler_sha,
        'compiler_checkout_head': head,
        'compiler_matches_run_head': True,
        'compiler_build_provenance': 'NOT_INDEPENDENTLY_VERIFIED',
        'archive_manifest_sha256': 'a' * 64,
        'original_selector_sha256': clocking_legacy.ORIGINAL_SELECTOR_SHA256,
        'original_selected_count': 438,
        'remaining_original_count': 436,
        'classification': 'INAPPLICABLE_REVERTED_CONTRACT',
        'audit_verified': True,
        'semantic_pass': False,
        'original_criteria_pass': False,
        'raw_returncode': 1,
        'raw_returncode_scope': 'DERIVED_FROM_BOTH_OBSERVED_NATIVE_FAILURES',
        'counts': {
            'passed': 0,
            'failed': 2
        },
        'cases': {
            name: {
                'summary_status': 'FAILED',
                'counts': {
                    'passed': 0,
                    'failed': 1
                },
                'actual_exit': 10,
                'raw_wait_status': 2560,
                'semantic_pass': False,
                'fingerprint_verified': True,
                'log_sha256': 'b' * 64,
            }
            for name in clocking_legacy.LEGACY_NAMES
        },
        'evidence_sha256': 'c' * 64,
        'global_status': 'HOLD',
    }


def wave_report(head, compiler_sha):
    """Typed wave evidence fixture; the waveform checker owns byte corruption controls."""
    return {
        'schema': 'clocking-wave-v1',
        'head': head,
        'compiler_sha256': compiler_sha,
        'semantic_pass': True,
        'cycles': 8,
        'output_skew_ps': 1,
        'checks': 474,
        'wave_sha256': 'd' * 64,
        'sim_log_sha256': 'e' * 64,
    }


def green_rows():
    """Generate individual harness records independently of aggregate counters."""
    rows = {}
    for group, selected in GROUPS.items():
        text = ''.join('vlt/t_' + name + ': Self PASSED\n' for name in selected)
        rows[group] = {
            'summary_status': 'PASSED',
            'counts': {
                'passed': len(selected),
                'failed': 0
            },
            'returncode': 0,
            'success': True,
            'passed_names_match': True,
            'actual_passed_names': actual_passed_names(text),
        }
    return rows


class SelectionProjectionTest(unittest.TestCase):
    """An unrelated failure and a new failure affect different denominators."""

    def test_original_and_revised_selections_have_distinct_identities(self):
        revision = selection_revision()
        self.assertEqual(revision['original_selected_drivers'], 438)
        self.assertEqual(revision['current_selected_drivers'], sum(map(len, GROUPS.values())))
        self.assertEqual(revision['current_selected_drivers'],
                         436 + len(revision['added_drivers']))
        self.assertEqual(revision['unchanged_drivers'], 436)
        self.assertEqual(revision['removed_drivers'],
                         ['clocking_output_iface', 'clocking_output_unsup'])
        self.assertTrue({'clocking_port_connections', 'fourstate_clocking_out_unsup'} <= set(
            revision['added_drivers']))
        self.assertNotEqual(revision['original_selector_sha256'],
                            revision['current_selector_sha256'])
        self.assertEqual(revision['original_selector_sha256'],
                         '665e70412e7e1a35b9c92758d67587975e152abbd17023a957657dfa2a4c9332')

    def test_original_projection_retains_two_failures(self):
        rows = green_rows()
        legacy = legacy_report('1' * 40, '2' * 64)
        projection = review.original_projection(review.regression_summary(rows), legacy)
        self.assertEqual(projection['counts']['passed'], 436)
        self.assertEqual(projection['counts']['failed'], 2)
        self.assertEqual(projection['selected_drivers'], 438)
        self.assertEqual(projection['head'], '1' * 40)
        self.assertEqual(projection['scope'], 'CURRENT_RUN_PROJECTED_ON_ORIGINAL_SELECTION')
        self.assertFalse(projection['semantic_pass'])
        self.assertFalse(projection['original_criteria_pass'])
        self.assertEqual(projection['strict_gate_exit'], 1)

    def test_new_failures_are_excluded_but_existing_failures_are_preserved(self):
        legacy = legacy_report('1' * 40, '2' * 64)
        for group, expected_passed, expected_failed in (('clocking_contract_20261031', 436, 2),
                                                        ('upstream_daily_20261014', 435, 3)):
            with self.subTest(group=group):
                rows = green_rows()
                row = rows[group]
                row['actual_passed_names'].pop()
                row.update(summary_status='FAILED',
                           returncode=10,
                           success=False,
                           passed_names_match=False)
                row['counts']['passed'] -= 1
                row['counts']['failed'] += 1
                projection = review.original_projection(review.regression_summary(rows), legacy)
                self.assertEqual(projection['counts']['passed'], expected_passed)
                self.assertEqual(projection['counts']['failed'], expected_failed)

    def test_later_new_driver_group_does_not_change_original_projection(self):
        current = selection_revision()
        with mock.patch.dict(GROUPS, {'later_compiler_controls': ['later_lvalue_control']}):
            revision = selection_revision()
            self.assertEqual(revision['current_selected_drivers'],
                             current['current_selected_drivers'] + 1)
            self.assertEqual(len(revision['added_drivers']), len(current['added_drivers']) + 1)
            projection = review.original_projection(review.regression_summary(green_rows()),
                                                    legacy_report('1' * 40, '2' * 64))
            self.assertEqual(projection['counts']['passed'], 436)
            self.assertEqual(projection['counts']['failed'], 2)
            self.assertEqual(projection['excluded_new_drivers'], len(current['added_drivers']) + 1)

    def test_counts_cannot_replace_missing_individual_pass_records(self):
        rows = green_rows()
        rows['upstream']['actual_passed_names'].pop()
        with self.assertRaisesRegex(ValueError, 'identity_count'):
            review.original_projection(review.regression_summary(rows),
                                       legacy_report('1' * 40, '2' * 64))


class MandatoryEvidenceTest(unittest.TestCase):
    """Missing, changed or unreviewed legacy evidence cannot use current green counts."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / 'out').mkdir()
        (self.root / 'bin').mkdir()
        (self.root / 'bin/verilator_bin').write_bytes(b'fixture compiler')
        self.head = '1' * 40
        compiler = hashlib.sha256(b'fixture compiler').hexdigest()
        self.legacy = legacy_report(self.head, compiler)
        self.wave = wave_report(self.head, compiler)
        patcher = mock.patch.object(clocking_legacy, 'audit', return_value=self.legacy)
        self.audit = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = mock.patch.object(review.clocking_wave, 'validate', return_value=self.wave)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.saved = check_results.clocking_evidence(self.root, self.head)
        self.save()

    def save(self):
        (self.root / 'out/clocking-legacy-evidence.json').write_text(json.dumps(self.saved))
        (self.root / 'out/clocking-wave-evidence.json').write_text(json.dumps(self.wave))

    def test_fresh_audit_is_required_even_with_valid_saved_evidence(self):
        review.clocking_files(self.root, self.head)
        self.audit.assert_called_with(self.root, self.root / 'out/clocking-legacy')
        for error in (FileNotFoundError('missing native log'),
                      ValueError('unknown failure fingerprint')):
            with self.subTest(error=str(error)), mock.patch.object(clocking_legacy,
                                                                   'audit',
                                                                   side_effect=error):
                with self.assertRaises(type(error)):
                    review.clocking_files(self.root, self.head)

    def test_missing_or_changed_typed_files_are_rejected(self):
        for name in ('clocking-legacy-evidence.json', 'clocking-wave-evidence.json'):
            path = self.root / 'out' / name
            original = path.read_bytes()
            path.unlink()
            with self.assertRaises(OSError):
                review.clocking_files(self.root, self.head)
            path.write_bytes(original)
        original = copy.deepcopy(self.saved)
        self.saved['legacy']['semantic_pass'] = 0
        self.save()
        with self.assertRaisesRegex(ValueError, 'saved_evidence_mismatch'):
            review.clocking_files(self.root, self.head)
        self.saved = original
        self.save()

    def test_unexpected_legacy_pass_or_mismatched_compiler_is_rejected(self):
        for field, value in (('semantic_pass', True), ('compiler_matches_run_head', False),
                             ('compiler_sha256', '0' * 64)):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.legacy)
                changed[field] = value
                with mock.patch.object(clocking_legacy, 'audit', return_value=changed):
                    with self.assertRaises(ValueError):
                        review.clocking_files(self.root, self.head)


if __name__ == '__main__':
    unittest.main()
