#!/usr/bin/env python3
# DESCRIPTION: Verilator: Signed, unsigned and unknown event NBA part-select bounds
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('vlt')
fourstate = test.name == 't_fourstate_nba_clip_bounds'
flags = ['--binary', '--sched-zero-delay', '--debug-check', '--build-jobs', '1']
if fourstate:
    flags += ['--fourstate', '-Wno-FUTURE']
test.compile(verilator_flags2=flags, make_flags=['-j1'])
test.execute()
cases = 22 if fourstate else 16
test.file_grep(test.run_log_filename, r'^Part-select bounds checks: (\d+)$', 9 * cases)
test.file_grep_count(test.run_log_filename, r'^BOUNDS STROBE ', cases)
for kind in range(cases):
    value = '0111' if kind in (0, 6, 9, 12) else ('1110' if kind == 2 else '0110')
    test.file_grep(test.run_log_filename,
                   f'^BOUNDS STROBE case={kind} t={3 * kind + 1} bank0={value} bank1=1001$')
test.passes()
