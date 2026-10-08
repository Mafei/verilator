#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap

test.scenarios('simulator')
test.top_filename = 't/t_timing_zero_domain.v'
test.compile(
    verilator_flags2=['--binary', '--fourstate', '--trace', '--sched-zero-delay', '-Wno-FUTURE'],
    v_flags2=['+define+ZERO_XZ'],
)
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Zero-domain checks: (\d+)', 39)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
test.passes()
