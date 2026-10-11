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
test.compile(
    verilator_flags2=['--binary', '--fourstate', '--trace', '--debug-check', '-Wno-FUTURE'])
test.execute()
test.file_grep(test.run_log_filename, r'^Four-state force release checks: (\d+)$', 64)

# Independent character vectors include every public state transition, not just
# the final known overwrite that could hide a stale unknown-bit force.
expected = {}
widths = {}
add(expected, widths, 't.total_checks', 32, '0' * 32)
add(expected, widths, 't.done', 4, '0000')
for width in (7, 33, 65, 95):
    scope = f't.w{width}.'
    forced = ''.join('01xz'[index % 4] for index in reversed(range(width)))
    known = format(13, f'0{width}b')
    for name in ('selected', 'packed_words'):
        add(expected, widths, scope + name, 2 * width, '0' * (2 * width))
    add(expected, widths, scope + 'whole', width, '0' * width)
    add(expected, widths, scope + 'checks', 32, '0' * 32)
    add(expected, widths, scope + 'done', 1, '0')
    append(expected, scope + 'selected', 1000, forced + '0' * width)
    append(expected, scope + 'packed_words', 1000, '0' * width + forced)
    append(expected, scope + 'whole', 1000, forced)
    append(expected, scope + 'selected', 2000, forced + '1' * width)
    append(expected, scope + 'packed_words', 2000, '1' * width + forced)
    append(expected, scope + 'selected', 4000, known + '1' * width)
    append(expected, scope + 'packed_words', 4000, '1' * width + known)
    append(expected, scope + 'whole', 4000, known)
    for timestamp, checks in ((2000, 5), (3000, 10), (4000, 13), (5000, 16)):
        append(expected, scope + 'checks', timestamp, format(checks, '032b'))
    append(expected, scope + 'done', 5000, '1')
for timestamp, checks in ((2000, 20), (3000, 40), (4000, 52), (5000, 64)):
    append(expected, 't.total_checks', timestamp, format(checks, '032b'))
append(expected, 't.done', 5000, '1111')
check_trace(test, expected, widths)
test.passes()
