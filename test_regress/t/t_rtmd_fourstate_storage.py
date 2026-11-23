#!/usr/bin/env python3
# DESCRIPTION: Verilator: Trace writes after a split coroutine resumes
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import json
from pathlib import Path
import vltest_bootstrap
from fourstate_resolve_oracle import check_trace
from fourstate_rtmd_trace_common import saif_records, declarations, check_vcd, check_fst

test.scenarios('vlt')
test.top_filename = 't/t_trace_cat.v'
test.compile(make_main=False,
             make_top_shell=False,
             verilator_flags2=[
                 '--cc', '--exe', '--no-timing', '--trace-fst', test.pli_filename,
                 'verilated_vcd_c.cpp', 'verilated_saif_c.cpp', '-CFLAGS', '-std=c++14'
             ])
test.execute()
widths_list = (1, 7, 8, 9, 15, 31, 32, 33, 64, 65, 95, 128, 129, 256, 257, 301)
times = (0, 3, 8, 15, 26)
expected = {}
for width in widths_list:
    for kind in ('s', 'alias', 'b', 'k'):
        states = '01xz' if kind != 'k' else '01'
        rows = []
        for phase, stamp in enumerate(times):
            chars = []
            for bit in reversed(range(width)):
                index = (bit + phase) % len(states)
                if kind == 'b': index = 3 - index
                chars.append(states[index])
            rows.append((stamp, ''.join(chars)))
        expected[f't.{kind}{width}'] = rows
widths = {name: len(rows[0][1]) for name, rows in expected.items()}
for profile in ('vcd', 'fst'):
    trace = test.obj_dir + '/storage.' + profile
    if profile == 'fst':
        check_fst(test, trace, expected, widths)
    else:
        check_vcd(test, trace, expected, widths)
        decls = declarations(Path(trace).read_text())
        for width in widths_list:
            a, alias, b = [decls[f't.{kind}{width}']['code'] for kind in ('s', 'alias', 'b')]
            if a != alias or a == b:
                test.error(f'{profile}: wrong RTMD plane-aware alias codes at width {width}')
previous = {}
checked = 0
for close_time, filename in ((26, 'short.saif'), (39, 'long.saif')):
    actual = saif_records(Path(test.obj_dir + '/' + filename).read_text())
    for name, rows in expected.items():
        for bit in range(widths[name]):
            key = name + (f'[{bit}]' if widths[name] > 1 else '')
            wanted = dict.fromkeys(('T0', 'T1', 'TX', 'TZ', 'TB', 'TC'), 0)
            prev = '0'
            for i, (start, value) in enumerate(rows):
                char = value[-1 - bit]
                end = rows[i + 1][0] if i + 1 < len(rows) else close_time
                wanted['T' + char.upper()] += end - start
                wanted['TC'] += int(char != prev)
                prev = char
            got = actual.get(key)
            if got != wanted: test.error(f'{filename}: {key}: {got}, expected {wanted}')
            if close_time == 26: previous[key] = got['TC'] if got else None
            elif got and got['TC'] != previous[key]: test.error('Close-time residence changed TC')
            checked += 1
Path(test.obj_dir + '/storage-oracle.json').write_text(
    json.dumps(
        {
            'expected_histories': expected,
            'saif_bit_records_checked': checked,
            'verified_constructed_counterexamples': 16,
            'close_times': [26, 39]
        },
        indent=2) + '\n')
print(f'RTMD runtime oracle: histories={len(expected)}, SAIF bit records={checked}')
test.passes()
