#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import PAIR, WIDTHS, add, append, check_trace, resolved

test.scenarios('simulator')
test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Resolver event checks: (\d+)', 4320)
test.file_grep(test.run_log_filename, r'Resolver packet checks: (\d+)', 476)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')


def pattern(width, offset=0):
    return ''.join('01xz'[(bit + offset) % 4] for bit in reversed(range(width)))


def source_values(width, phase):
    a = ['0', '0', '0', 'z', 'z', 'x', 'z', 'z', 'x', '1', '1', '1',
         pattern(width), pattern(width), pattern(width), 'z']
    b = ['z', '1', '1', '1', 'z', 'z', 'z', '0', '0', '0', '0', 'z',
         'z', pattern(width, 1), 'z', 'z']
    a2, b2 = a[phase], b[phase]
    a3 = pattern(width) if phase == 15 else a2
    b3 = pattern(width, 1) if phase >= 14 else b2
    c3 = pattern(width, 2) if phase == 14 else 'z'
    return [value * width if len(value) == 1 else value for value in (a2, b2, a3, b3, c3)]


expected = {}
widths = {}
for width in WIDTHS:
    owner = f'w{width}'
    for source in ('a2', 'b2', 'a3', 'b3', 'c3'):
        add(expected, widths, owner + '.source_' + source, width, 'z' * width)
    for group in (2, 3):
        for net in PAIR:
            stem = owner + f'.r{group}_{net}'
            for name, bits, value in ((stem, width, 'z' * width),
                                      (stem + '_snapshot', width, 'z' * width),
                                      (stem + '_events', 32, '0' * 32),
                                      (stem + '_time', 64, '0' * 64),
                                      (stem + '_realtime', 0, '0')):
                add(expected, widths, name, bits, value)
    for phase in range(16):
        timestamp = 1125 + phase * 125
        a2, b2, a3, b3, c3 = source_values(width, phase)
        for source, value in zip(('a2', 'b2', 'a3', 'b3', 'c3'), (a2, b2, a3, b3, c3)):
            append(expected, owner + '.source_' + source, timestamp, value)
        for group, sources in ((2, (a2, b2[::-1])), (3, (a3, b3[::-1], c3))):
            for net in PAIR:
                stem = owner + f'.r{group}_{net}'
                value = resolved(net, *sources)
                if value != expected[stem][-1][1]:
                    count = len(expected[stem])
                    append(expected, stem, timestamp, value)
                    append(expected, stem + '_snapshot', timestamp, value)
                    append(expected, stem + '_events', timestamp, format(count, '032b'))
                    append(expected, stem + '_time', timestamp, format((timestamp + 500) // 1000, '064b'))
                    append(expected, stem + '_realtime', timestamp, str(timestamp / 1000).removesuffix('.0'))
for width in (1, 17, 24, 31, 32, 63, 64):
    owner = f'p{width}'
    add(expected, widths, owner + '.source_a', width, '0' * width)
    add(expected, widths, owner + '.source_b', width, pattern(width))
    for source in ('a', 'b'):
        add(expected, widths, owner + '.disabled_' + source, 1, '1')
    for net in PAIR:
        add(expected, widths, owner + '.resolved_' + net, width, 'z' * width)
    for phase in range(8):
        timestamp = 1125 + phase * 125
        a = ('0' if phase == 0 else '1' if phase == 1 else 'x' if phase == 2 else 'z') * width
        b = pattern(width) if phase < 6 else '1' * width
        da, db = phase >= 4, phase < 5 or phase == 7
        append(expected, owner + '.source_a', timestamp, a)
        append(expected, owner + '.source_b', timestamp, b)
        append(expected, owner + '.disabled_a', timestamp, str(int(da)))
        append(expected, owner + '.disabled_b', timestamp, str(int(db)))
        # Verilog bitwise complement maps both X and Z to X; it never releases.
        ca = 'z' * width if da else ''.join({'0': '1', '1': '0', 'x': 'x', 'z': 'x'}[c] for c in a)
        cb = 'z' * width if db else b
        for net in PAIR:
            append(expected, owner + '.resolved_' + net, timestamp, resolved(net, ca, cb))
check_trace(test, expected, widths)
test.passes()
