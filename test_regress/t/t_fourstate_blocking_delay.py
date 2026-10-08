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
        '--sched-zero-delay',
        '-Wno-FUTURE',
        '-Wno-IEEEMAYDEPRECATE',
        '-Wno-LITENDIAN',
    ]
)
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Blocking delay checks: (\d+)', 306)
expected = {}
widths = {}


def pattern(width, seed):
    return ''.join('01xz'[(bit + seed) % 4] for bit in reversed(range(width)))


for width in (1, 7, 17, 33, 65, 129):
    prefix = f'w{width}.'
    zero, one, floating = '0' * width, '1' * width, 'z' * width
    first, second = pattern(width, 1), pattern(width, 2)
    for name, timeline in (
        (
            'source',
            (
                (10, first),
                (11, second),
                (14, floating),
                (18, one),
                (25, second),
                (26, first),
                (27, zero),
            ),
        ),
        ('result', ((13, first), (17, floating), (21, one), (25, second), (26, first), (27, zero))),
        (
            'fork_source',
            (
                (30, pattern(width, 2)),
                (32, pattern(width, 3)),
                (34, zero),
                (40, floating),
                (42, one),
                (44, zero),
            ),
        ),
        (
            'fork_result',
            ((35, pattern(width, 3)), (37, pattern(width, 2)), (45, one), (47, floating)),
        ),
    ):
        add(expected, widths, prefix + name, width, zero)
        for timestamp, value in timeline:
            append(expected, prefix + name, timestamp, value)
    add(expected, widths, prefix + 'fork_follow', width, zero)
    for timestamp, value in (
        (35, pattern(width, 3)),
        (37, pattern(width, 2)),
        (45, one),
        (47, floating),
    ):
        literal = ''.join(
            str(int(a) ^ int(b)) if a in '01' and b in '01' else 'x'
            for a, b in zip(pattern(width, 0), value)
        )
        append(expected, prefix + 'fork_follow', timestamp, literal)
    for name, times in (
        ('rhs_calls', (10, 14, 18, 25, 26, 27)),
        ('delay_calls', (10, 14, 18, 25, 26, 27)),
        ('completions', (13, 17, 21, 25, 26, 27)),
        ('events', (13, 17, 21, 25, 26, 27)),
        ('fork_rhs_calls', (31, 33, 41, 43)),
        ('fork_delay_calls', (31, 33, 41, 43)),
        ('fork_completions', (35, 37, 45, 47)),
        ('fork_events', (35, 37, 45, 47)),
    ):
        add(expected, widths, prefix + name, 32, '0' * 32)
        for count, timestamp in enumerate(times, start=1):
            append(expected, prefix + name, timestamp, f'{count:032b}')
    for name, times in (
        ('next_time', (13, 17, 21, 25, 26, 27)),
        ('last_change', (13, 17, 21, 25, 26, 27)),
        ('fork_next_time', (35, 37, 45, 47)),
        ('fork_last_change', (35, 37, 45, 47)),
    ):
        add(expected, widths, prefix + name, 64, '0' * 64)
        for timestamp in times:
            append(expected, prefix + name, timestamp, f'{timestamp:064b}')
check_trace(test, expected, widths)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
test.passes()
