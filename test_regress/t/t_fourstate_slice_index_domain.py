#!/usr/bin/env python3
# DESCRIPTION: Verilator: Complete signed/unsigned domains for indexed four-state reads
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
test.compile(verilator_flags2=[
    '--binary', '--fourstate', '-Wno-FUTURE', '--trace', '--debug-check', '--build-jobs', '1'
],
             make_flags=['-j1'])
test.execute()
test.file_grep(test.run_log_filename, r'^Slice domain checks: (\d+)$', 3840)
test.file_grep_count(test.run_log_filename, r'^SLICE READ ', 80)
expected = {}
widths = {}
names = ['s4', 'u4', 's32', 'u32', 's64', 'u64', 's95', 'u95']
for width in (7, 33, 65, 95):
    for group in ('r', 'm'):
        for name in names:
            signal = f't.w{width}.{group}_{name}'
            expected[signal] = []
            widths[signal] = 3
    for roundno in range(2):
        for kind in range(10):
            step = 10 * roundno + kind
            data = ['01xz'[(bit + roundno + kind) % 4] for bit in range(width)]
            offsets = [[0] * 8, [-1, 15, -1, None, -1, None, -1, None], [7, 15] + [width - 2] * 6,
                       [-2, 14, -2, None, -2, None, -2,
                        None], [-3, 8] + [None] * 6, [7, 15] + [None] * 6, [None] * 8, [None] * 8,
                       [1, 8] + [31] * 6, [3] * 8][kind]
            values = []
            for group, adjustment in (('r', 0), ('m', -2)):
                for name, offset in zip(names, offsets):
                    # Address each bit mathematically, with no index truncation or modulo.
                    base = None if offset is None else offset + adjustment
                    selected = [
                        'x' if base is None or not 0 <= base + bit < width else data[base + bit]
                        for bit in range(3)
                    ]
                    value = ''.join(reversed(selected))
                    values.append((f'{group}_{name}', value))
                    signal = f't.w{width}.{group}_{name}'
                    if not expected[signal] or expected[signal][-1][1] != value:
                        expected[signal].append((2 * step, value))
            fields = ''.join(f' {name}={value}' for name, value in values)
            test.file_grep(
                test.run_log_filename,
                f'^SLICE READ W={width} round={roundno} case={kind} t={2 * step + 1}{fields}$')
check_trace(test, expected, widths)
test.passes()
