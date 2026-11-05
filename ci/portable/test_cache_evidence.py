#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Keep infrastructure failures separate from truthful passing model records."""
# pylint: disable=missing-function-docstring

import copy
import json
from pathlib import Path
import tempfile
import unittest

import cache_evidence


class CacheEvidenceTest(unittest.TestCase):
    """Reject absent, incomplete or misleading cache-reclamation evidence."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / 'out').mkdir()
        self.head = 'a' * 40
        self.groups = {'example_group': ['example']}
        prefix = 'test_regress/obj_vlt/t_example/Vexample'
        self.data = {
            'schema': 'portable-compile-cache-results-v1',
            'commit': self.head,
            'groups': {
                'example_group': {
                    'schema':
                    'completed-compile-cache-v1',
                    'status':
                    'complete',
                    'selected': ['example'],
                    'bytes':
                    15,
                    'removed': [
                        {
                            'path': prefix + '.o',
                            'bytes': 5,
                            'kind': 'generated_object',
                            'rebuild_source': prefix + '.cpp'
                        },
                        {
                            'path': prefix + '__pch.h.fast.gch',
                            'bytes': 10,
                            'kind': 'generated_precompiled_header',
                            'rebuild_source': prefix + '__pch.h'
                        },
                    ],
                },
            },
        }

    def write(self, data):
        (self.root / 'out/compile-cache-results.json').write_text(json.dumps(data))

    def check(self):
        return cache_evidence.validate(self.root, self.head, self.groups)

    def test_complete_relocated_ledger(self):
        self.data['groups']['example_group']['root'] = '/another/producer/checkout'
        self.write(self.data)
        self.assertEqual(self.check(), self.data)

    def test_missing_or_stale_ledger(self):
        with self.assertRaises(OSError):
            self.check()
        for change in ({'commit': 'b' * 40}, {'groups': {}}, {'schema': 'unknown'}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.write({**self.data, **change})
                self.check()

    def test_incomplete_selection_or_failed_cleanup(self):
        for change in ({
                'status': 'infrastructure_failure'
        }, {
                'status': 'in_progress'
        }, {
                'selected': ['another']
        }, {
                'bytes': True
        }, {
                'bytes': 16
        }):
            with self.subTest(change=change), self.assertRaises(ValueError):
                data = copy.deepcopy(self.data)
                data['groups']['example_group'].update(change)
                self.write(data)
                self.check()

    def test_unrecoverable_or_outside_paths_are_rejected(self):
        for change in ({
                'path': '/tmp/outside.o'
        }, {
                'path': 'test_regress/obj_vlt/t_example/../Vexample.o'
        }, {
                'path': 'test_regress/obj_vlt/t_unselected/Vexample.o'
        }, {
                'path': 'test_regress/obj_vlt/t_example/model'
        }, {
                'rebuild_source': 'original.sv'
        }, {
                'kind': 'archive'
        }, {
                'bytes': False
        }):
            with self.subTest(change=change), self.assertRaises(ValueError):
                data = copy.deepcopy(self.data)
                data['groups']['example_group']['removed'][0].update(change)
                self.write(data)
                self.check()

    def test_duplicate_removed_path_is_rejected(self):
        row = self.data['groups']['example_group']
        row['removed'].append(copy.deepcopy(row['removed'][0]))
        row['bytes'] += 5
        self.write(self.data)
        with self.assertRaises(ValueError):
            self.check()


if __name__ == '__main__':
    unittest.main()
