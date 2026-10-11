#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_port_oracle import port_partial
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
test.compile(verilator_flags2=[
    '--binary', '--fourstate', '--trace', '--trace-depth', '2', '--debug-check', '-Wno-FUTURE',
    '-Wno-ASCRANGE', '--output-split', '10000', '--output-split-cfuncs', '100'
])
test.execute()
test.file_grep(test.run_log_filename, r'^Partial output port checks: (\d+)$', 380)
expected, widths = port_partial()
check_trace(test, expected, widths)
test.passes()
