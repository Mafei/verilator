#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Record both upload outcomes outside the frozen payload and require publication."""

import json
import os
from pathlib import Path
import re


def attempt(name, context):
    """Retain the action outcome before continue-on-error changes its conclusion."""
    outputs = context.get('outputs', {})
    return {
        'name': name,
        'outcome': context.get('outcome', ''),
        'conclusion': context.get('conclusion', ''),
        'artifact_id': outputs.get('artifact-id', ''),
        'artifact_digest': outputs.get('artifact-digest', ''),
        'artifact_url': outputs.get('artifact-url', '')
    }


def finalized(row):
    """A successful action must also report its finalized artifact metadata."""
    return (row['outcome'] == 'success'
            and re.fullmatch(r'[1-9][0-9]*', row['artifact_id']) is not None
            and re.fullmatch(r'[0-9a-f]{64}', row['artifact_digest']) is not None)


def upload_result(name, primary, retry):
    """Accept a primary success or one successful retry after a primary failure."""
    attempts = [attempt(name, primary), attempt(name + '-retry1', retry)]
    selected = None
    if finalized(attempts[0]):
        selected = 0
    elif attempts[0]['outcome'] == 'failure' and finalized(attempts[1]):
        selected = 1
    return {
        'schema': 'artifact-upload-result-v1',
        'scope': 'artifact_transport_only; producer_and_semantic_gates_unchanged',
        'attempts': attempts,
        'selected_attempt': selected,
        'recovered': selected == 1,
        'gate_exit': int(selected is None)
    }


def main():
    """Publish the failed attempt too, then preserve a failed transport gate."""
    result = upload_result(os.environ['ARTIFACT_UPLOAD_NAME'],
                           json.loads(os.environ['ARTIFACT_UPLOAD_PRIMARY']),
                           json.loads(os.environ['ARTIFACT_UPLOAD_RETRY']))
    ledger = json.dumps(result, sort_keys=True, separators=(',', ':'))
    print('ARTIFACT_UPLOAD_RESULT ' + ledger, flush=True)
    with Path(os.environ['GITHUB_OUTPUT']).open('a', encoding='utf-8') as stream:
        stream.write('ledger=' + ledger + '\n')
    with Path(os.environ['GITHUB_STEP_SUMMARY']).open('a', encoding='utf-8') as stream:
        stream.write('### Artifact upload attempts\n\n```json\n' +
                     json.dumps(result, sort_keys=True, indent=2) + '\n```\n\n')
    return result['gate_exit']


if __name__ == '__main__':
    raise SystemExit(main())
