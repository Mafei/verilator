#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import PAIR, STATES, WIDTHS, add, append, check_trace, resolved

test.scenarios('simulator')
test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Pair primary checks: (\d+)', 768)
test.file_grep(test.run_log_filename, r'Pair constant dynamic checks: (\d+)', 384)
test.file_grep(test.run_log_filename, r'Pair constant pair checks: (\d+)', 768)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
expected = {}
widths = {}
for width in WIDTHS:
    for order in ('forward', 'reverse'):
        owner = f'w{width}.{order}'
        for name in ('source_a', 'source_b', *(f'resolved_{net}' for net in PAIR)):
            add(expected, widths, owner + '.' + name, width, 'z' * width)
        a = b = 'z' * width
        for phase in range(16):
            for stage in range(2):
                timestamp = 1125 + phase * 250 + stage * 125
                if stage == 0:
                    a = STATES[phase // 4] * width
                    append(expected, owner + '.source_a', timestamp, a)
                else:
                    b = STATES[phase % 4] * width
                    append(expected, owner + '.source_b', timestamp, b)
                for net in PAIR:
                    append(expected, owner + '.resolved_' + net, timestamp, resolved(net, a, b))
    for constant in range(2):
        for order in range(2):
            owner = f'w{width}.d{constant}{order}'
            a = str(constant) * width
            add(expected, widths, owner + '.source', width, 'z' * width)
            for net in PAIR:
                add(expected, widths, owner + '.resolved_' + net, width, a)
            for phase in range(4):
                timestamp = 1125 + phase * 250
                b = STATES[phase] * width
                append(expected, owner + '.source', timestamp, b)
                for net in PAIR:
                    append(expected, owner + '.resolved_' + net, timestamp, resolved(net, a, b))
    for a in range(4):
        for b in range(4):
            for order in range(2):
                owner = f'w{width}.c{a}{b}{order}'
                for net, table in PAIR.items():
                    value = table[a * 4 + b] * width
                    add(expected, widths, owner + '.resolved_' + net, width, value)
check_trace(test, expected, widths)
test.passes()
