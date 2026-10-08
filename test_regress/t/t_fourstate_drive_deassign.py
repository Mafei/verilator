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
test.file_grep(test.run_log_filename, r'Deassign checks: (\d+)', 102)
expected = {}
widths = {}
# Literal effective-value history; active NBA/blocking writes must never leak.
for width in (1, 7, 17, 33, 65, 129):
    path = f'w{width}.observed'
    add(expected, widths, path, width, '0' * width)
    for timestamp, value in (
        (10, 'z'),
        (13, 'x'),
        (15, 'z'),
        (18, '1'),
        (19, 'x'),
        (20, '0'),
        (24, 'z'),
    ):
        append(expected, path, timestamp, value * width)
    add(expected, widths, f'w{width}.events', 32, '0' * 32)
    add(expected, widths, f'w{width}.last_change', 64, '0' * 64)
    for count, timestamp in enumerate((10, 13, 15, 18, 19, 20, 24), start=1):
        append(expected, f'w{width}.events', timestamp, f'{count:032b}')
        append(expected, f'w{width}.last_change', timestamp, f'{timestamp:064b}')
check_trace(test, expected, widths)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
test.passes()
