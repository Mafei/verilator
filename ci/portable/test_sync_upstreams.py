#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Exercise the sync contract using tiny, offline Git repositories only."""

from contextlib import redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


SPEC = importlib.util.spec_from_file_location('sync_upstreams', Path(__file__).with_name('sync_upstreams.py'))
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True, stderr=subprocess.PIPE).strip()


def identity(repo):
    git(repo, 'config', 'user.name', 'Sync fixture')
    git(repo, 'config', 'user.email', 'fixture@example.invalid')
    git(repo, 'config', 'commit.gpgsign', 'false')
    git(repo, 'config', 'core.hooksPath', '/dev/null')


def commit(repo, filename, content):
    (repo / filename).write_text(content, encoding='utf-8')
    git(repo, 'add', filename)
    git(repo, 'commit', '--quiet', '-m', 'Update fixture')
    return git(repo, 'rev-parse', 'HEAD')


class SyncTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='verilator-sync-test-', dir='/tmp')
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        common = self.directory / 'common'
        common.mkdir()
        git(common, 'init', '--quiet', '-b', 'master')
        identity(common)
        self.base = commit(common, 'README', 'common\n')
        self.repo = self.directory / 'source'
        self.veripool = self.directory / 'veripool'
        self.antmicro = self.directory / 'antmicro'
        for destination in (self.repo, self.veripool, self.antmicro):
            git(self.directory, 'clone', '--quiet', '--no-local', common.as_uri(), str(destination))
            identity(destination)
        git(self.antmicro, 'branch', 'dev/fourstate', self.base)
        git(self.antmicro, 'branch', 'feature/4_state_logic', self.base)
        # Repo-local URL rewrites keep the production endpoint selection intact
        # while every fetch in this test remains a local file operation.
        git(self.repo, 'config', 'protocol.file.allow', 'always')
        git(self.repo, 'config', 'url.' + self.veripool.as_uri() + '.insteadOf', SYNC.UPSTREAMS[0][1])
        git(self.repo, 'config', 'url.' + self.antmicro.as_uri() + '.insteadOf', SYNC.UPSTREAMS[1][1])
        self.worktree = self.directory / 'candidate-worktree'
        self.report_file = self.directory / 'provenance.json'

    def run_sync(self, candidate=False):
        arguments = ['--repo', str(self.repo), '--base', 'master', '--report', str(self.report_file)]
        if candidate:
            arguments += ['--candidate', 'sync-candidate', '--worktree', str(self.worktree)]
        output = io.StringIO()
        with redirect_stdout(output):
            code = SYNC.main(arguments)
        report = json.loads(output.getvalue())
        self.assertNotIn(str(self.directory), output.getvalue())
        if self.report_file.exists():
            self.assertEqual(report, json.loads(self.report_file.read_text(encoding='utf-8')))
        return code, report

    def add_upstream_changes(self):
        official = commit(self.veripool, 'official.txt', 'Veripool update\n')
        git(self.antmicro, 'checkout', '--quiet', 'dev/fourstate')
        fourstate = commit(self.antmicro, 'fourstate.txt', 'Four-state update\n')
        git(self.antmicro, 'checkout', '--quiet', 'feature/4_state_logic')
        logic = commit(self.antmicro, 'logic.txt', 'Other four-state update\n')
        return (official, fourstate, logic)

    def test_no_update_does_not_create_candidate(self):
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 0)
        self.assertEqual(report['status'], 'up_to_date')
        self.assertFalse(report['updates_available'])
        self.assertFalse(self.worktree.exists())
        self.assertIsNone(SYNC.read_ref(self.repo, 'refs/heads/sync-candidate'))
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.base)

    def test_audit_does_not_change_source_branch(self):
        tips = self.add_upstream_changes()
        code, report = self.run_sync()
        self.assertEqual(code, 0)
        self.assertEqual(report['status'], 'audit_complete')
        self.assertTrue(report['updates_available'])
        self.assertNotIn('candidate', report)
        self.assertEqual(tuple(item['commit'] for item in report['upstreams']), tips)
        self.assertEqual(report['upstreams'][0]['changed_files'], ['official.txt'])
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.base)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')
        self.assertEqual(git(self.repo, 'for-each-ref', '--format=%(refname)', 'refs/portable-sync'), '')

    def test_actual_merges_follow_fixed_order_and_preserve_base(self):
        tips = self.add_upstream_changes()
        original = commit(self.repo, 'ours.txt', 'Local four-state work\n')
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 0)
        self.assertEqual(report['status'], 'candidate_ready')
        previous = original
        for step, tip in zip(report['candidate']['merges'], tips):
            self.assertEqual(step['status'], 'merged')
            self.assertEqual(git(self.repo, 'show', '-s', '--format=%P', step['head']).split(), [previous, tip])
            previous = step['head']
        self.assertEqual(report['candidate']['head'], previous)
        for tip in tips + (original,):
            self.assertTrue(SYNC.ancestor(self.repo, tip, previous))
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), original)
        self.assertEqual(git(self.repo, 'symbolic-ref', '--short', 'HEAD'), 'master')
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')
        self.assertEqual(git(self.worktree, 'status', '--porcelain'), '')

    def test_conflict_stops_and_records_relative_paths(self):
        upstream = commit(self.veripool, 'README', 'upstream alternative\n')
        original = commit(self.repo, 'README', 'local alternative\n')
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 1)
        self.assertEqual(report['status'], 'conflict')
        self.assertEqual(len(report['candidate']['merges']), 1)
        self.assertEqual(report['candidate']['merges'][0]['unmerged_files'], ['README'])
        self.assertEqual(git(self.worktree, 'rev-parse', 'MERGE_HEAD'), upstream)
        self.assertEqual(git(self.worktree, 'rev-parse', 'HEAD'), original)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), original)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_existing_candidate_is_rejected_without_fetching(self):
        self.add_upstream_changes()
        git(self.repo, 'branch', 'sync-candidate')
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 2)
        self.assertEqual(report['status'], 'blocked')
        self.assertIn('already exists', report['error'])
        self.assertEqual(report['upstreams'], [])
        self.assertFalse(self.worktree.exists())

    def test_rewound_upstream_preserves_last_observed_commit(self):
        updated = commit(self.veripool, 'official.txt', 'Update later rewound\n')
        self.assertEqual(self.run_sync()[0], 0)
        git(self.veripool, 'reset', '--hard', self.base)
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 2)
        self.assertTrue(report['upstreams'][0]['rewound_or_replaced'])
        self.assertFalse(report['observation_refs_updated'])
        self.assertEqual(SYNC.read_ref(self.repo, 'refs/portable-upstreams/veripool-master'), updated)
        self.assertFalse(self.worktree.exists())

    def test_dirty_index_is_detected_even_when_worktree_matches_head(self):
        (self.repo / 'README').write_text('staged change\n', encoding='utf-8')
        git(self.repo, 'add', 'README')
        (self.repo / 'README').write_text('common\n', encoding='utf-8')
        self.assertEqual(git(self.repo, 'diff', 'HEAD', '--name-only'), '')
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 2)
        self.assertEqual(report['dirty_files'], ['README'])
        self.assertEqual(report['upstreams'], [])
        self.assertFalse(self.worktree.exists())

    def test_existing_worktree_path_is_rejected(self):
        self.worktree.mkdir()
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 2)
        self.assertEqual(report['upstreams'], [])
        self.assertIsNone(SYNC.read_ref(self.repo, 'refs/heads/sync-candidate'))

    def test_report_inside_source_is_rejected_without_writing(self):
        self.report_file = self.repo / 'provenance.json'
        code, report = self.run_sync()
        self.assertEqual(code, 2)
        self.assertIn('outside', report['error'])
        self.assertFalse(self.report_file.exists())
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_unrelated_history_is_rejected(self):
        git(self.veripool, 'checkout', '--quiet', '--orphan', 'replacement')
        git(self.veripool, 'rm', '--quiet', '-rf', '.')
        commit(self.veripool, 'unrelated.txt', 'Unrelated root\n')
        git(self.veripool, 'branch', '-M', 'master')
        code, report = self.run_sync(candidate=True)
        self.assertEqual(code, 2)
        self.assertEqual(report['upstreams'][0]['relation'], 'unrelated')
        self.assertFalse(report['observation_refs_updated'])
        self.assertFalse(self.worktree.exists())

    def test_fetch_failure_does_not_advance_observations(self):
        git(self.antmicro, 'branch', '-D', 'feature/4_state_logic')
        code, report = self.run_sync()
        self.assertEqual(code, 2)
        self.assertFalse(report['observation_refs_updated'])
        self.assertEqual(git(self.repo, 'for-each-ref', '--format=%(refname)', 'refs/portable-upstreams'), '')
        self.assertEqual(git(self.repo, 'for-each-ref', '--format=%(refname)', 'refs/portable-sync'), '')


if __name__ == '__main__':
    unittest.main()
