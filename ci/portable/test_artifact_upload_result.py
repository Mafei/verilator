#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Exercise upload recovery and fatal gates without network requests or HDL models."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

import artifact_upload_result as upload

ROOT = Path(__file__).resolve().parents[2]
ACTION = 'actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02'
NAME = 'macos-arm64-123-attempt2'
DIGEST = 'a' * 64


def context(outcome, artifact_id='', digest='', conclusion=None):
    """Model the documented step context, including continue-on-error's conclusion."""
    return {
        'outcome': outcome,
        'conclusion': conclusion or outcome,
        'outputs': {
            'artifact-id': artifact_id,
            'artifact-digest': digest,
            'artifact-url':
            'https://github.com/example/repo/actions/runs/123/artifacts/' + artifact_id
        }
    }


class UploadResultTest(unittest.TestCase):
    """Transport success requires an actual successful action with final metadata."""

    def test_primary_success_needs_no_retry(self):
        result = upload.upload_result(NAME, context('success', '123', DIGEST), {
            'outcome': 'skipped',
            'conclusion': 'skipped'
        })
        self.assertEqual(result['gate_exit'], 0)
        self.assertEqual(result['selected_attempt'], 0)
        self.assertFalse(result['recovered'])
        self.assertEqual(result['attempts'][1]['outcome'], 'skipped')

    def test_retry_success_keeps_the_failed_primary(self):
        result = upload.upload_result(NAME, context('failure', conclusion='success'),
                                      context('success', '456', DIGEST))
        self.assertEqual(result['gate_exit'], 0)
        self.assertEqual(result['selected_attempt'], 1)
        self.assertTrue(result['recovered'])
        self.assertEqual(result['attempts'][0]['outcome'], 'failure')
        self.assertEqual(result['attempts'][0]['conclusion'], 'success')
        self.assertEqual(result['attempts'][1]['name'], NAME + '-retry1')

    def test_both_failures_are_fatal_despite_success_conclusions(self):
        result = upload.upload_result(NAME, context('failure', '123', DIGEST, 'success'),
                                      context('failure', '456', DIGEST, 'success'))
        self.assertEqual(result['gate_exit'], 1)
        self.assertIsNone(result['selected_attempt'])
        self.assertEqual([row['outcome'] for row in result['attempts']], ['failure', 'failure'])

    def test_skipped_or_cancelled_uploads_cannot_supply_success(self):
        for outcome in ('skipped', 'cancelled', ''):
            with self.subTest(outcome=outcome):
                result = upload.upload_result(NAME, context(outcome, '123', DIGEST),
                                              context('skipped'))
                self.assertEqual(result['gate_exit'], 1)

    def test_retry_cannot_replace_a_skipped_or_cancelled_primary(self):
        for outcome in ('skipped', 'cancelled', ''):
            with self.subTest(outcome=outcome):
                result = upload.upload_result(NAME, context(outcome),
                                              context('success', '456', DIGEST))
                self.assertEqual(result['gate_exit'], 1)

    def test_success_without_finalized_metadata_is_fatal(self):
        for artifact_id, digest in (('', DIGEST), ('0', DIGEST), ('123\n', DIGEST), ('123', ''),
                                    ('123', 'a' * 63), ('123', 'z' * 64)):
            for retry in (False, True):
                with self.subTest(artifact_id=artifact_id, digest=digest, retry=retry):
                    success = context('success', artifact_id, digest)
                    result = upload.upload_result(NAME,
                                                  context('failure') if retry else success,
                                                  success if retry else context('skipped'))
                    self.assertEqual(result['gate_exit'], 1)

    def assert_cli_result(self, primary, retry, status):
        with self.subTest(status=status), tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            payload = root / 'out'
            payload.mkdir()
            frozen = payload / 'producer-core-review.json'
            frozen.write_text('{"semantic_gate_exit":1}\n', encoding='utf-8')
            runner = root / 'runner'
            runner.mkdir()
            output = runner / 'output'
            summary = runner / 'summary'
            output.write_text('existing_output=preserved\n', encoding='utf-8')
            env = os.environ.copy()
            env.update(ARTIFACT_UPLOAD_NAME=NAME,
                       ARTIFACT_UPLOAD_PRIMARY=json.dumps(primary),
                       ARTIFACT_UPLOAD_RETRY=json.dumps(retry),
                       GITHUB_OUTPUT=str(output),
                       GITHUB_STEP_SUMMARY=str(summary),
                       PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run(
                [sys.executable,
                 str(ROOT / 'ci/portable/'
                     'artifact_upload_result.py')],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=10)
            self.assertEqual(result.returncode, status, result.stdout + result.stderr)
            lines = output.read_text().splitlines()
            self.assertEqual(lines[0], 'existing_output=preserved')
            ledger = json.loads(lines[1].removeprefix('ledger='))
            self.assertEqual(ledger['gate_exit'], status)
            self.assertEqual(result.stdout,
                             'ARTIFACT_UPLOAD_RESULT ' + lines[1][len('ledger='):] + '\n')
            self.assertIn(json.dumps(ledger, sort_keys=True, indent=2), summary.read_text())
            self.assertEqual(frozen.read_text(), '{"semantic_gate_exit":1}\n')
            self.assertEqual(list(payload.iterdir()), [frozen])

    def test_cli_publishes_success_and_failure_without_touching_payload(self):
        self.assert_cli_result(context('success', '123', DIGEST), context('skipped'), 0)
        self.assert_cli_result(context('failure', conclusion='success'),
                               context('success', '456', DIGEST), 0)
        self.assert_cli_result(context('failure', conclusion='success'),
                               context('failure', conclusion='success'), 1)


class WorkflowPolicyTest(unittest.TestCase):
    """Keep every upload bounded and its final gate independent of semantic failure."""

    def setUp(self):
        source = (ROOT / '.github/workflows/portable-fourstate.yml').read_text()
        parts = re.split(r'^  ([a-z0-9-]+):\n', source.split('jobs:\n', 1)[1], flags=re.M)
        self.jobs = dict(zip(parts[1::2], parts[2::2]))
        self.policies = []
        for job, text in self.jobs.items():
            blocks = re.split(r'(?=^      - )', text, flags=re.M)[1:]
            for i, block in enumerate(blocks):
                if not re.search(r'^        id: upload_\w+_primary$', block, re.M):
                    continue
                self.assertGreaterEqual(len(blocks) - i, 4)
                self.policies.append((job, blocks[i:i + 4]))

    @staticmethod
    def field(block, key, indent=8):
        match = re.search(r'^' + ' ' * indent + re.escape(key) + r': (.+)$', block, re.M)
        return match[1] if match else None

    def test_all_five_uploads_have_exactly_one_retry_and_gate(self):
        self.assertEqual(len(self.policies), 5)
        self.assertEqual(sum(text.count('uses: ' + ACTION) for text in self.jobs.values()), 10)
        for job, (primary, backoff, retry, gate) in self.policies:
            with self.subTest(job=job, artifact=self.field(primary, 'id')):
                stem = self.field(primary, 'id').removesuffix('_primary')
                self.assertEqual(self.field(backoff, 'id'), stem + '_backoff')
                self.assertEqual(self.field(retry, 'id'), stem + '_retry')
                self.assertEqual(self.field(gate, 'id'), stem + '_result')
                self.assertEqual(self.field(primary, 'uses'), ACTION)
                self.assertEqual(self.field(retry, 'uses'), ACTION)
                self.assertEqual(self.field(backoff, 'run'), 'sleep 15')
                self.assertEqual(self.field(primary, 'continue-on-error'), 'true')
                self.assertEqual(self.field(retry, 'continue-on-error'), 'true')
                self.assertIsNone(self.field(gate, 'continue-on-error'))
                self.assertEqual(self.field(gate, 'run'),
                                 'python3 ci/portable/artifact_upload_result.py')
                self.assertIn('always() && !cancelled()', self.field(primary, 'if'))
                self.assertEqual(self.field(primary, 'if'), self.field(gate, 'if'))
                self.assertEqual(
                    self.field(backoff, 'if'),
                    "${{ !cancelled() && steps." + stem + "_primary.outcome == 'failure' }}")
                self.assertEqual(
                    self.field(retry, 'if'), "${{ !cancelled() && steps." + stem +
                    "_primary.outcome == 'failure' && steps." + stem +
                    "_backoff.outcome == 'success' }}")
                self.assertEqual(self.field(gate, 'ARTIFACT_UPLOAD_PRIMARY', 10),
                                 '${{ toJSON(steps.' + stem + '_primary) }}')
                self.assertEqual(self.field(gate, 'ARTIFACT_UPLOAD_RETRY', 10),
                                 '${{ toJSON(steps.' + stem + '_retry) }}')
                self.assertIn('${{ steps.' + stem + '_result.outputs.ledger }}', self.jobs[job])

    def test_payload_alias_names_and_options_cannot_overwrite_first_attempt(self):
        for job, (primary, _, retry, gate) in self.policies:
            with self.subTest(job=job, artifact=self.field(primary, 'id')):
                name = self.field(primary, 'name', 10)
                self.assertIn('${{ github.run_id }}-attempt${{ github.run_attempt }}', name)
                self.assertEqual(self.field(retry, 'name', 10), name + '-retry1')
                self.assertEqual(self.field(gate, 'ARTIFACT_UPLOAD_NAME', 10), name)
                anchor = self.field(primary, 'path', 10).split()[0]
                self.assertTrue(anchor.startswith('&'))
                self.assertEqual(self.field(retry, 'path', 10), '*' + anchor[1:])
                for block in (primary, retry):
                    self.assertEqual(self.field(block, 'if-no-files-found', 10), 'error')
                    self.assertIsNone(self.field(block, 'overwrite', 10))

    def test_clocking_raw_wave_is_retained_for_both_platforms(self):
        wave = 'test_regress/obj_vlt/t_clocking_port_connections/simx.vcd'
        main = [(job, primary) for job, (primary, _, _, _) in self.policies
                if self.field(primary, 'id') == 'upload_main_primary']
        self.assertEqual({job for job, _ in main}, {'macos', 'rocky8'})
        for job, primary in main:
            with self.subTest(job=job):
                self.assertEqual(primary.count(wave), 1)

    def test_semantic_steps_are_fatal_and_producer_review_precedes_upload(self):
        for job, text in self.jobs.items():
            for block in re.split(r'(?=^      - )', text, flags=re.M)[1:]:
                if self.field(block, 'continue-on-error') is not None:
                    self.assertEqual(self.field(block, 'uses'), ACTION)
            self.assertNotRegex(text, r'(?m)^    continue-on-error:')
            if job != 'artifact-review':
                self.assertLess(text.index('id: producer_review'),
                                text.index('id: upload_main_primary'))
                self.assertIn('core_review: ${{ steps.producer_review.outputs.core_review }}',
                              text)


if __name__ == '__main__':
    unittest.main()
