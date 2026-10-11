#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import add, append, check_trace

test.scenarios('vlt')
# Bit variables also need constant packed offsets in the four-state pipeline.
test.compile(
    verilator_flags2=['--binary', '--fourstate', '--trace', '--debug-check', '-Wno-FUTURE'])
test.execute()
test.file_grep(test.run_log_filename, r'^Packed selector release checks: (\d+)$', 36)

expected = {}
widths = {}
add(expected, widths, 't.total_checks', 32, '0' * 32)
add(expected, widths, 't.done', 2, '00')
for width in (65, 95):
    scope = f't.w{width}.'
    low = ''.join('01'[index % 2] for index in reversed(range(width)))
    high = ''.join('10'[index % 2] for index in reversed(range(width)))
    six = format(6, f'0{width}b')
    ten = format(10, f'0{width}b')
    add(expected, widths, scope + 'words', 2 * width, '0' * (2 * width))
    add(expected, widths, scope + 'checks', 32, '0' * 32)
    add(expected, widths, scope + 'done', 1, '0')
    append(expected, scope + 'words', 1000, high + low)
    append(expected, scope + 'words', 4000, high + six)
    append(expected, scope + 'words', 6000, ten + six)
    append(expected, scope + 'words', 7000, low + high)
    append(expected, scope + 'words', 9000, '0' * (2 * width))
    for timestamp in range(2000, 10001, 1000):
        append(expected, scope + 'checks', timestamp, format(2 * (timestamp // 1000 - 1), '032b'))
    append(expected, scope + 'done', 10000, '1')
for timestamp in range(2000, 10001, 1000):
    append(expected, 't.total_checks', timestamp, format(4 * (timestamp // 1000 - 1), '032b'))
append(expected, 't.done', 10000, '11')
check_trace(test, expected, widths)
test.passes()
