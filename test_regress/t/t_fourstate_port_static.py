#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_port_oracle import port_static
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
test.compile(verilator_flags2=[
    '--binary', '--fourstate', '--trace', '--trace-depth', '2', '--debug-check', '-Wno-FUTURE',
    '--output-split', '10000', '--output-split-cfuncs', '100'
])
test.execute()
test.file_grep(test.run_log_filename, r'^Static port storage checks: (\d+)$', 24)
expected, widths = port_static()
check_trace(test, expected, widths)
test.passes()
