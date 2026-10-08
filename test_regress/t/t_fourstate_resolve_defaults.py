#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import WIDTHS, add, append, check_trace

test.scenarios('simulator')
test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Resolver default checks: (\d+)', 1296)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')


def pattern(width, offset):
    return ''.join('01xz'[(bit + offset) % 4] for bit in reversed(range(width)))


def stimulus(width, phase):
    uniform = {0: '1', 1: 'x', 2: 'z', 3: '0', 9: '1', 10: 'z', 11: '0'}
    if phase in uniform:
        return uniform[phase] * width
    return pattern(width, min(phase - 4, 3))


expected = {}
widths = {}
for width in WIDTHS:
    owner = f'w{width}'
    add(expected, widths, owner + '.source', width, '0' * width)
    defaults = {'zero': '0' * width, 'one': '1' * width,
                'mixed_x': pattern(width, 2), 'mixed_z': pattern(width, 3)}
    for flavor, default in defaults.items():
        for mode in ('omitted', 'open', 'connected'):
            value = '0' * width if mode == 'connected' else default
            add(expected, widths, owner + '.' + flavor + '_' + mode, width, value)
    for name, bits, value in (('connected_snapshot', width, '0' * width),
                             ('connected_events', 32, '0' * 32),
                             ('connected_time', 64, '0' * 64),
                             ('connected_realtime', 0, '0')):
        add(expected, widths, owner + '.' + name, bits, value)
    for phase in range(12):
        timestamp = 1125 + phase * 125
        value = stimulus(width, phase)
        append(expected, owner + '.source', timestamp, value)
        for flavor in defaults:
            append(expected, owner + '.' + flavor + '_connected', timestamp, value)
        key = owner + '.connected_snapshot'
        if expected[key][-1][1] != value:
            count = len(expected[key])
            append(expected, key, timestamp, value)
            append(expected, owner + '.connected_events', timestamp, format(count, '032b'))
            append(expected, owner + '.connected_time', timestamp, format((timestamp + 500) // 1000, '064b'))
            append(expected, owner + '.connected_realtime', timestamp, str(timestamp / 1000).removesuffix('.0'))
check_trace(test, expected, widths)
test.passes()
