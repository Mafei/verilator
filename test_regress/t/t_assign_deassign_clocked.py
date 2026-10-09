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
test.compile(verilator_flags2=['--binary', '--trace', '-Wno-IEEEMAYDEPRECATE'])
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Clocked deassign bit checks: (\d+)', 64)
expected = {}
widths = {}
for width in (1, 7, 33, 65):
    for prefix in ('c', 'd'):
        path = f'{prefix}{width}.q'
        add(expected, widths, path, width, '0' * width)
        for timestamp, value in ((10, '1'), (16, '0'), (17, '1')):
            append(expected, path, timestamp, value * width)
check_trace(test, expected, widths)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:')
test.passes()
