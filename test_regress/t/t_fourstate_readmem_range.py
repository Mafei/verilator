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
test.compile(verilator_flags2=['--binary', '--fourstate', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename)
test.file_grep(test.run_log_filename, r'Readmem range checks: (\d+)', 152)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:')
if test.iv:
    # Icarus explicitly reports its standards-era choice for descending default
    # and start-only declarations. Assert every such warning, without hiding it.
    test.file_grep_count(test.run_log_filename, r'^WARNING:', 3)
    test.file_grep_count(test.run_log_filename, r'^WARNING:.*Defaulting to 1364-2005 behavior', 3)
else:
    test.file_grep_not(test.run_log_filename, r'%Warning|WARNING:')
test.passes()
