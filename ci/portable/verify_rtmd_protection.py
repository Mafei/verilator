#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Fail before building if published protected bytes or the inherited selection change."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

from run_regressions import selection_revision


def main():
    """Use the explicit baseline hashes even in a shallow final-SHA checkout."""
    root = Path(__file__).resolve().parents[2]
    manifest = root / 'ci/portable/rtmd-20261123/protected-paths.json'
    manifest_hash = hashlib.sha256(manifest.read_bytes()).hexdigest()
    if manifest_hash != '322f6cb77f9ee34faf256096f1bf53f54bf7c39abc5759bcac66cb751b9a82c5':
        raise ValueError('Protected baseline manifest identity changed')
    items = json.loads(manifest.read_text(encoding='utf-8'))
    if len(items) != 2057 or len({row['path'] for row in items}) != 2057:
        raise ValueError('Protected baseline inventory changed')
    bad = []
    for row in items:
        path = root / row['path']
        if (not path.is_file() or path.stat().st_size != row['bytes']
                or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']):
            bad.append(row['path'])
    selection = selection_revision()  # Also checks the ordered 898-driver prefix.
    result = {
        'head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'manifest_sha256': manifest_hash,
        'protected_paths': len(items),
        'mismatches': bad,
        'selection': selection,
        'protected_bytes_verified': not bad
    }
    output = root / 'out/rtmd-protection.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('RTMD_PROTECTION ' + json.dumps(result), flush=True)
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
