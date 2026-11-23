#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Report original trace values separately from protected declaration/golden failures."""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def audit_original(root, obj, profile):
    """Derive the original fixture's complete histories without changing its golden."""
    sys.path.insert(0, str(root / 'test_regress/t'))
    from fourstate_resolve_oracle import check_trace  # pylint: disable=import-outside-toplevel
    from fourstate_rtmd_trace_common import declarations  # pylint: disable=import-outside-toplevel
    wave = obj / ('simx.' + profile)
    if not wave.is_file():
        return {'status': 'NOT_RUN_OR_NO_WAVE'}

    class Probe:
        """Use the original character-vector checker without rewriting a file."""
        trace_filename = str(wave)

        def error(self, message):
            raise ValueError(message)

    expected = {}
    widths = (1, 8, 9, 32, 33, 64, 65, 128, 129, 256, 257, 301)
    for i, width in enumerate(widths):
        expected[f't.s{i}'] = [(0, 'x' * width), (10, '0' * (width - 1) + '1'), (20, '0' * width),
                               (30, 'z' * width), (40, 'x' * width)]
    expected['t.foo'] = [(0, '0' * 14), (10, '0' * 13 + '1'), (20, '0' * 14)]
    try:
        if profile == 'fst':
            from fourstate_rtmd_trace_common import check_fst
            probe = Probe()
            probe.obj_dir = str(obj)
            fst_proof = check_fst(probe, str(wave), expected, {
                n: len(rows[0][1])
                for n, rows in expected.items()
            })
        else:
            check_trace(Probe(), expected, {n: len(rows[0][1]) for n, rows in expected.items()})
    except ValueError as error:
        return {'status': 'SEMANTIC_MISMATCH', 'error': str(error)}
    rows = declarations(wave.read_text()) if profile == 'vcd' else {}
    proof = {
        'status':
        'SEMANTIC_HISTORIES_MATCH',
        'histories':
        expected,
        'declarations': {
            name: rows.get(name)
            for name in expected
        },
        'protected_golden_result':
        'UNMODIFIED; use original driver status separately',
        'known_structure_delta':
        'RTMD preserves source range [0:0] on s0; legacy golden declares a scalar'
    }
    if profile == 'fst': proof['fst_audit'] = fst_proof
    (obj / 'independent-histories.json').write_text(json.dumps(proof, indent=2) + '\n')
    return proof
