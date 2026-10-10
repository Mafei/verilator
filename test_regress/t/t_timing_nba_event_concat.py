#!/usr/bin/env python3
# DESCRIPTION: Verilator: Event-controlled NBA concat capture and scheduling
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
fourstate = test.name == 't_fourstate_nba_event_concat'
flags = ['--binary', '--trace', '--sched-zero-delay', '--debug-check', '-Wno-ASCRANGE']
if fourstate:
    flags += ['--fourstate', '-Wno-FUTURE']
test.compile(verilator_flags2=flags)
test.execute()
test.file_grep(test.run_log_filename, r'^Event NBA checks: (\d+)$', 116)

# Independent literal patterns, indexed from the MSB in these Python strings.
# VCD checks use physical timestamps; caller/#0 assertions establish ordering.
cycles = '0zx1' if fourstate else '0011'
expected = {
    name: [(0, '0' * width)]
    for name, width in {
        't.bank1_view': 65,
        't.bank2_view': 65,
        't.a33': 33,
        't.b65': 65,
        't.asc': 33,
        't.plain': 65,
    }.items()
}
for phase in range(4):
    rhs = ''.join(cycles[(index - phase) % 4] for index in range(65))
    rhs_asc = ''.join(cycles[(index - phase - 1) % 4] for index in range(33))
    values = {
        't.bank1_view': '0' * 57 + rhs[33:40] + '0',
        't.bank2_view': '0' * 31 + rhs[:33] + '0',
        't.a33': '0' * 17 + rhs[40:55] + '0',
        't.b65': '0' * 54 + rhs[55:] + '0',
        't.asc': rhs_asc,
        't.plain': rhs,
    }
    timestamp = 3 * phase + 2
    for key, value in values.items():
        if expected[key][-1][1] != value:
            expected[key].append((timestamp, value))
    line = (f'^NBA STROBE round={phase} t={timestamp} bank1={values["t.bank1_view"]}'
            f' bank2={values["t.bank2_view"]} a33={values["t.a33"]}'
            f' b65={values["t.b65"]} asc={values["t.asc"]}'
            f' plain={values["t.plain"]}$')
    test.file_grep(test.run_log_filename, line)
check_trace(test, expected, {name: len(values[0][1]) for name, values in expected.items()})
test.passes()
