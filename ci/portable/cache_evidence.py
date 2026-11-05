#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Require completed compilation-cache reclamation without changing model results."""

import json
from pathlib import PurePosixPath


def validate(root, head, groups):
    """Check the independent infrastructure ledger, including relocated artifacts."""
    data = json.loads((root / 'out/compile-cache-results.json').read_text())
    if (not isinstance(data, dict) or data.get('schema') != 'portable-compile-cache-results-v1'
            or data.get('commit') != head or not isinstance(data.get('groups'), dict)
            or set(data['groups']) != set(groups)):
        raise ValueError('compile_cache_provenance_or_selection')
    for group, selected in groups.items():
        row = data['groups'][group]
        if (not isinstance(row, dict) or row.get('schema') != 'completed-compile-cache-v1'
                or row.get('status') != 'complete' or row.get('selected') != selected
                or type(row.get('bytes')) is not int or row['bytes'] < 0
                or not isinstance(row.get('removed'), list)):
            raise ValueError('compile_cache_incomplete: ' + group)
        total = 0
        paths = set()
        for item in row['removed']:
            if (not isinstance(item, dict) or not isinstance(item.get('path'), str)
                    or not isinstance(item.get('rebuild_source'), str)
                    or type(item.get('bytes')) is not int or item['bytes'] < 0):
                raise ValueError('compile_cache_record_type: ' + group)
            path = PurePosixPath(item['path'])
            source = PurePosixPath(item['rebuild_source'])
            if (path.is_absolute() or source.is_absolute() or '..' in path.parts
                    or '..' in source.parts or len(path.parts) < 4
                    or path.parts[:2] != ('test_regress', 'obj_vlt')
                    or path.parts[2] not in {'t_' + name
                                             for name in selected} or item['path'] in paths):
                raise ValueError('compile_cache_path: ' + group)
            kind = item.get('kind')
            if kind == 'runtime_object':
                valid = (source.parts == ('include', path.stem + '.cpp')
                         and path.name.startswith('verilated') and path.suffix == '.o')
            elif kind == 'generated_object':
                valid = source == path.with_suffix('.cpp') and path.suffix == '.o'
            elif kind == 'generated_precompiled_header':
                valid = (path.name.endswith(('__pch.h.fast.gch', '__pch.h.slow.gch'))
                         and source == path.with_name(path.name.rsplit('.', 2)[0]))
            else:
                valid = False
            if not valid:
                raise ValueError('compile_cache_rebuild_source: ' + group)
            paths.add(item['path'])
            total += item['bytes']
        if total != row['bytes']:
            raise ValueError('compile_cache_bytes: ' + group)
    return data
