#!/usr/bin/env python3
# DESCRIPTION: Verilator: Repeat event counts and NBA capture
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
fourstate = test.name == 't_fourstate_nba_repeat_control'
flags = ['--binary', '--trace', '--sched-zero-delay', '--debug-check']
if fourstate:
    flags += ['--fourstate', '-Wno-FUTURE']
test.compile(verilator_flags2=flags)
test.execute()
test.file_grep(test.run_log_filename, r'^Repeat NBA checks: (\d+)$', 80 if fourstate else 73)
for event, values in enumerate([
        '0054 bank2=0000 bank3=0000 shadow1=0096 shadow2=0000 shadow3=0000',
        '0054 bank2=0150 bank3=0000 shadow1=0096 shadow2=00d4 shadow3=0000',
        '0054 bank2=0150 bank3=01e0 shadow1=0096 shadow2=00d4 shadow3=0330',
],
                               start=1):
    test.file_grep(test.run_log_filename,
                   f'^REPEAT STROBE event={event} t={event} bank1={values}$')
expected = {}
for name, value, timestamp in [
    ('bank1', 0x54, 1),
    ('bank2', 0x150, 2),
    ('bank3', 0x1e0, 3),
    ('shadow1', 0x96, 1),
    ('shadow2', 0xd4, 2),
    ('shadow3', 0x330, 3),
]:
    expected['t.' + name] = [(0, '0' * 15), (timestamp, format(value, '015b'))]
for name, value in [('zero_q', 0x2a), ('negative_q', 0x35)]:
    expected['t.' + name] = [(0, format(value, '07b'))]
for name in ['wide_q', 'unsigned_q', 'blocking1']:
    expected['t.' + name] = [(0, '0' * 7)]
expected['t.blocking2'] = [(0, '0' * 7), (6, 'xz10z01' if fourstate else '0100101')]
check_trace(test, expected, {name: len(values[0][1]) for name, values in expected.items()})
test.passes()
