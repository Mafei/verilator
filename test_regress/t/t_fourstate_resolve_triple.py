#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import vltest_bootstrap
from fourstate_resolve_oracle import STATES, TRIPLE, add, append, check_trace, resolved

test.scenarios('simulator')
test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename, iv_run_flags=['-N'])
test.file_grep(test.run_log_filename, r'Triple checks: (\d+)', 1536)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')
expected = {}
widths = {}
for order in range(6):
    owner = f'p{order}'
    for name in ('source_a', 'source_b', 'source_c', *(f'resolved_{net}' for net in TRIPLE)):
        add(expected, widths, owner + '.' + name, 1, 'z')
    sources = ['z', 'z', 'z']
    for phase in range(64):
        target = (STATES[phase // 16], STATES[(phase // 4) % 4], STATES[phase % 4])
        for stage, source_name in enumerate(('source_a', 'source_b', 'source_c')):
            timestamp = 1125 + phase * 375 + stage * 125
            sources[stage] = target[stage]
            append(expected, owner + '.' + source_name, timestamp, target[stage])
            for net in TRIPLE:
                append(expected, owner + '.resolved_' + net, timestamp, resolved(net, *sources))
check_trace(test, expected, widths)
test.passes()
