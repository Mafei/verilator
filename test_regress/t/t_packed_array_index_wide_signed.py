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
test.timeout(60)
test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'^Packed wide signed index checks: (\d+)$', 18)
test.file_grep_count(test.run_log_filename, r'^PASS packed_array_index_wide_signed$', 1)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')

expected = {}
widths = {}
for index_width in (32, 65, 95):
    for name, known, unknown in (('out_one', '1010101', '101x001'),
                                 ('out_two', '0101010', 'x010110'), ('out_three', '0010011',
                                                                     '11010xx')):
        key = f'w{index_width}.{name}'
        add(expected, widths, key, 7, '0000000')
        append(expected, key, 1000, known)
        append(expected, key, 2000, unknown)
check_trace(test, expected, widths)
test.passes()
