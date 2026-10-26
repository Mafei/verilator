#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import check_trace

test.scenarios('vlt')
fourstate = test.name == 't_fourstate_inout_default'
flags = ['--binary', '--trace', '--build-jobs', '1']
if fourstate:
    flags += ['--fourstate', '-Wno-FUTURE']
test.compile(verilator_flags2=flags, make_flags=['-j1'])
test.execute()
test.file_grep(test.run_log_filename, r'^Floating inout checks: (\d+)$', 330 if fourstate else 120)
expected = {}
widths = {}
for width in (1, 7, 33, 65, 95):
    if fourstate:
        for prefix in ('bare', 'connected', 'interface'):
            for kind in ('wire', 'tri', 'wand', 'wor', 'triand', 'trior'):
                name = f't.w{width}.{prefix}_{kind}'
                widths[name] = width
                expected[name] = [(0, 'z' * width)]
    pulls = [('pulled_down', '0'), ('pulled_up', '1'), ('child_down', '0'), ('child_up', '1')]
    if not fourstate:
        pulls += [('connected_down', '0'), ('connected_up', '1'), ('explicit_down', '0'),
                  ('explicit_up', '1')]
    for name, value in pulls:
        name = f't.w{width}.{name}'
        widths[name] = width
        expected[name] = [(0, value * width)]
check_trace(test, expected, widths)
test.passes()
