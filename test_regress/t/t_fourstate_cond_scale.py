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
# Ascending packed ranges deliberately exercise assignment direction.
test.timeout(180)
test.compile(
    verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE', '-Wno-ASCRANGE'])
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Conditional scale checks: (\d+)', 4416)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')


def pattern(width, phase, flavor):
    value = []
    for bit in reversed(range(width)):
        offset = flavor
        if flavor == 1 and phase % 4 == 2 and bit % 2 == 0:
            offset = 0
        state = '01xz'[(bit + phase + offset) % 4]
        if phase % 8 in (5, 6) and state == 'z':
            state = 'x'
        value.append(state)
    return ''.join(value)


def merged(a, b):
    return ''.join(left if left == right else 'x' for left, right in zip(a, b))


def conditional(state, a, b):
    if state == '0':
        return b
    if state == '1':
        return a
    return merged(a, b)


expected = {}
widths = {}
for width in WIDTHS:
    owner = f'w{width}'
    outputs = ('result20', 'result32', 'result64', 'result128', 'up_result', 'function_result',
               'nested_result', 'vector7_result', 'vector65_result')
    for name in outputs:
        add(expected, widths, owner + '.' + name, width, '0' * width)
    for phase in range(32):
        timestamp = (phase + 1) * 1000
        left = pattern(width, phase, 0)
        right = pattern(width, phase, 1)
        middle = pattern(width, phase, 2)
        kind = phase % 8
        chain = right if kind == 0 else merged(left, right) if kind in (3, 4, 7) else left
        for name in outputs[:4]:
            append(expected, owner + '.' + name, timestamp, chain)
        selector = '01xz'[phase % 4]
        simple = conditional(selector, left, right)
        for name in ('up_result', 'function_result'):
            append(expected, owner + '.' + name, timestamp, simple)
        inner = conditional('01xz'[(phase // 4) % 4], middle, right)
        append(expected, owner + '.nested_result', timestamp, conditional(selector, left, inner))
        vector = right if kind == 0 else left if kind in (1, 4, 5) else merged(left, right)
        for name in ('vector7_result', 'vector65_result'):
            append(expected, owner + '.' + name, timestamp, vector)
check_trace(test, expected, widths)
print(f'Conditional trace checks: {len(expected)}')
test.passes()
