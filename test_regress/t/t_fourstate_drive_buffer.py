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
test.file_grep(test.run_log_filename, r'Buffer dynamic checks: (\d+)', 16128)
test.file_grep(test.run_log_filename, r'Buffer constant checks: (\d+)', 64)
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
check_trace(test, expected, widths)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
test.passes()
