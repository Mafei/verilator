#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import add, append, check_trace

test.scenarios('simulator')
test.compile(
    verilator_flags2=[
        '--binary',
        '--fourstate',
        '--trace',
        '--stats',
        '-Wno-FUTURE',
        '-Wno-IEEEMAYDEPRECATE',
        '-Wno-LITENDIAN',
    ]
)
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
if test.vlt_all:
    test.file_grep(test.stats, r'Fourstate, Isolated tristate buffers\s+(\d+)', 128)
test.file_grep(test.run_log_filename, r'Buffer dynamic checks: (\d+)', 24192)
test.file_grep(test.run_log_filename, r'Buffer constant checks: (\d+)', 68)
test.file_grep(test.run_log_filename, r'Buffer expression checks: (\d+)', 29568)
expected = {}
widths = {}
states = '01xz'
tables = ('zzzz01xxxxxxxxxx', '01xxzzzzxxxxxxxx', 'zzzz10xxxxxxxxxx', '10xxzzzzxxxxxxxx')
for width in (1, 7, 17, 33, 65, 129):
    owner = f'w{width}.'
    for name in ('source_enable', 'source_data'):
        add(expected, widths, owner + name, width, '0' * width)
    names = ('buffer1', 'buffer0', 'inverter1', 'inverter0')
    for kind, name in enumerate(names):
        add(expected, widths, owner + name, width, tables[kind][0] * width)
    for name in ('plain_buffer0', 'plain_buffer1'):
        add(expected, widths, owner + name, width, '0' * width)
    for phase in range(16):
        timestamp = 10 + phase * 11
        en = [((phase % 4 + bitno) % 4) for bitno in reversed(range(width))]
        data = [((phase // 4 + bitno) % 4) for bitno in reversed(range(width))]
        append(expected, owner + 'source_enable', timestamp, ''.join(states[x] for x in en))
        append(expected, owner + 'source_data', timestamp, ''.join(states[x] for x in data))
        for kind, name in enumerate(names):
            append(
                expected,
                owner + name,
                timestamp,
                ''.join(tables[kind][e * 4 + d] for e, d in zip(en, data)),
            )
        for name in ('plain_buffer0', 'plain_buffer1'):
            append(expected, owner + name, timestamp, ''.join('01xx'[d] for d in data))

for width in (17, 24, 31, 32, 63, 64):
    owner = f'x{width}.'
    inputs = ('enable_a', 'data_a', 'enable_b', 'data_b', 'data_c', 'known_enable')
    values = {key: '0' * width for key in inputs}
    for key, value in values.items():
        add(expected, widths, owner + key, width, value)
    add(expected, widths, owner + 'branch', 1, '0')
    add(expected, widths, owner + 'result_a', width, 'z' * width)
    add(expected, widths, owner + 'result_b', width, '1' * width)
    add(expected, widths, owner + 'result_known', width, 'z' * width)
    add(expected, widths, owner + 'result_plain', width, '0' * width)
    choose = '0'
    for phase in range(32):
        timestamp = 10 + phase * 3
        bitnos = list(reversed(range(width)))
        values['enable_a'] = ''.join(states[(phase % 4 + bitno) % 4] for bitno in bitnos)
        values['data_a'] = ''.join(states[(phase // 4 + bitno) % 4] for bitno in bitnos)
        if phase % 2 == 0:
            values['enable_b'] = ''.join(states[(phase % 4 + bitno + 1) % 4] for bitno in bitnos)
            values['data_b'] = ''.join(states[(phase // 4 + bitno + 1) % 4] for bitno in bitnos)
            values['data_c'] = ''.join(states[(phase // 8 + 3 * bitno + 1) % 4] for bitno in bitnos)
            values['known_enable'] = ''.join(str((phase // 2 + bitno) % 2) for bitno in bitnos)
            choose = states[(phase // 4) % 4]
        for key, value in values.items():
            append(expected, owner + key, timestamp, value)
        append(expected, owner + 'branch', timestamp, choose)
        rotated_enable = values['enable_a'][1:] + values['enable_a'][:1]
        rotated_data = values['data_a'][1:] + values['data_a'][:1]
        merged = ''.join(
            b if choose == '1' else c if choose == '0' else b if b == c else 'x'
            for b, c in zip(values['data_b'], values['data_c'])
        )
        result_a = ''.join(
            tables[0][states.index(e) * 4 + states.index(d)]
            for e, d in zip(rotated_enable, rotated_data)
        )
        result_b = ''.join(
            tables[3][states.index(e) * 4 + states.index(d)]
            for e, d in zip(values['enable_b'], merged)
        )
        known_enable = values['known_enable'][1:] + values['known_enable'][:1]
        known_data = values['data_c'][1:] + values['data_c'][:1]
        result_known = ''.join(
            tables[0][int(e) * 4 + states.index(d)] for e, d in zip(known_enable, known_data)
        )
        append(expected, owner + 'result_a', timestamp, result_a)
        append(expected, owner + 'result_b', timestamp, result_b)
        append(expected, owner + 'result_known', timestamp, result_known)
        append(
            expected,
            owner + 'result_plain',
            timestamp,
            ''.join('01xx'[states.index(d)] for d in known_data),
        )
check_trace(test, expected, widths)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
test.passes()
