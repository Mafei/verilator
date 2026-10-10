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
test.compile(verilator_flags2=[
    '--binary', '--fourstate', '--trace', '--trace-depth', '2', '--debug-check', '-Wno-FUTURE',
    '-Wno-ASCRANGE'
])
test.execute()
test.file_grep(test.run_log_filename, r'^Packed port kind checks: (\d+)$', 600)

# Character vectors independently describe packed ordering and X/Z projection.
# Physical timestamps do not establish event-region order.
expected = {}
widths = {}
add(expected, widths, 't.total_checks', 32, '0' * 32)
for width in (7, 33, 65, 95):
    scope = f't.w{width}.'
    add(expected, widths, scope + 'data', width, '0' * width)
    for name, default in (('ca_variable', 'x'), ('ca_explicit_variable', 'x'),
                          ('ca_net', 'z'), ('ca_bit', '0'), ('port_bit', '0')):
        add(expected, widths, scope + name, 2 * width, default * width + '0' * width)
    for name, default in (('port_variable', 'x'), ('port_explicit_variable', 'x'),
                          ('port_net', 'z')):
        add(expected, widths, scope + name, 6 * width, default * (3 * width) + '0' * (3 * width))
    add(expected, widths, scope + 'no_writer_variable', width, 'x' * width)
    add(expected, widths, scope + 'no_writer_net', width, 'z' * width)
    add(expected, widths, scope + 'checks', 32, '0' * 32)
    add(expected, widths, scope + 'done', 1, '0')
    values = [
        ''.join('01xz'[index % 4] for index in reversed(range(width))),
        ''.join('1' if index % 3 == 1 else '0' for index in reversed(range(width))),
        'z' * width,
        'x' * width,
        ''.join('0' if index % 3 == 1 else '1' for index in reversed(range(width))),
    ]
    for phase, value in enumerate(values):
        timestamp = (phase + 1) * 1000
        append(expected, scope + 'data', timestamp, value)
        for name, default in (('ca_variable', 'x'), ('ca_explicit_variable', 'x'), ('ca_net', 'z')):
            append(expected, scope + name, timestamp, default * width + value)
        bit_value = ''.join('1' if char == '1' else '0' for char in value)
        for name in ('ca_bit', 'port_bit'):
            append(expected, scope + name, timestamp, '0' * width + bit_value)
        rotated = {item: value[item:] + value[:item] for item in (1, 2, 3)}
        descending = rotated[3] + rotated[2] + rotated[1]
        ascending = rotated[1] + rotated[2] + rotated[3]
        append(expected, scope + 'port_variable', timestamp, 'x' * (3 * width) + descending)
        append(expected, scope + 'port_explicit_variable', timestamp, 'x' * (3 * width) + ascending)
        append(expected, scope + 'port_net', timestamp, 'z' * (3 * width) + descending)
        append(expected, scope + 'checks', timestamp + 1000, format(30 * (phase + 1), '032b'))
    append(expected, scope + 'done', 6000, '1')
for phase in range(5):
    append(expected, 't.total_checks', (phase + 2) * 1000, format(120 * (phase + 1), '032b'))
check_trace(test, expected, widths)
test.passes()
