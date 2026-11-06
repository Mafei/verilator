#!/usr/bin/env python3
# DESCRIPTION: Verilator: Class-task discard sinks survive delayed NBA callbacks
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

from pathlib import Path

import vltest_bootstrap

test.scenarios('vlt')
test.compile(
    verilator_flags2=['--binary', '--trace', '--fourstate', '--sched-zero-delay', '-Wno-FUTURE'])
test.execute()
test.file_grep(test.run_log_filename, r'CLASS_NBA_BOUNDS_PASS checks=(\d+)', 10)
test.file_grep_not(test.run_log_filename, r'%Error|%Warning')

# Independent transitions in units fixed by the source's 1ps precision.
expected = {
    'bank0': [(0, '00000000'), (2000, '10xz01z1')],
    'bank1': [(0, '00000000'), (2000, 'z10x1100')],
}
test.file_grep(test.trace_filename, r'\$timescale\s+1ps\s+\$end')
scopes = []
codes = {}
actual = {name: [] for name in expected}
timestamp = 0
for line in Path(test.trace_filename).read_text(encoding='ascii').splitlines():
    words = line.split()
    if not words:
        continue
    if words[0] == '$scope':
        scopes.append(words[2])
    elif words[0] == '$upscope':
        scopes.pop()
    elif words[0] == '$var' and scopes and scopes[-1] == 't':
        if words[4] in expected:
            if int(words[2]) != 8:
                test.error('Class bounds trace signal width changed')
            codes.setdefault(words[3], []).append(words[4])
    elif words[0].startswith('#'):
        timestamp = int(words[0][1:])
    elif words[0].startswith('b'):
        value = words[0][1:].lower()
        for name in codes.get(words[1], []):
            value = value.rjust(8, value[0] if value[0] in 'xz' else '0')
            history = actual[name]
            if not history or history[-1][1] != value:
                history.append((timestamp, value))
if actual != expected:
    test.error(f'Class bounds VCD transitions differ: {actual}, expected {expected}')
print('Class bounds trace checks: 4')
test.passes()
