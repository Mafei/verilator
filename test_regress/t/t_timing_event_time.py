#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import re

import vltest_bootstrap

test.scenarios('simulator')
test.compile(verilator_flags2=['--binary', '--trace'])
test.execute(logfile=test.run_log_filename)
test.file_grep(test.run_log_filename, r'Event time checks: (\d+)', 24)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')

vector1 = 1 << 128
vector2 = vector1 | (1 << 64)
vector3 = vector2 | (1 << 32)
expected = {
    'scalar': [(0, '0'), (1250, '1'), (2000, '0')],
    'vector': [(0, '0' * 129), (1250, format(vector1, '0129b')),
               (2000, format(vector2, '0129b')), (3000, format(vector3, '0129b'))],
    'scalar_time': [(0, '0' * 64), (1250, format(1, '064b')), (2000, format(2, '064b'))],
    'vector_time': [(0, '0' * 64), (1250, format(1, '064b')),
                    (2000, format(2, '064b')), (3000, format(3, '064b'))],
    'scalar_real': [(0, 0.0), (1250, 1.25), (2000, 2.0)],
    'vector_real': [(0, 0.0), (1250, 1.25), (2000, 2.0), (3000, 3.0)],
}
with open(test.trace_filename, encoding='ascii') as stream:
    trace = stream.read()
if not re.search(r'\$timescale\s+1ps\s+\$end', trace):
    test.error('Event time trace does not use the expected 1ps precision')
codes = {}
events = {name: {} for name in expected}
timestamp = 0
for line in trace.splitlines():
    line = line.lstrip()
    declaration = re.match(r'\$var \w+ (\d+) (\S+) (\w+) ', line)
    if declaration and declaration[3] in expected:
        codes[declaration[2]] = (declaration[3], int(declaration[1]))
    if line.startswith('#'):
        timestamp = int(line[1:])
    vector_value = re.match(r'b([01xzXZ]+) (\S+)', line)
    real_value = re.match(r'r(\S+) (\S+)', line)
    scalar_value = re.match(r'([01xzXZ])(\S+)', line)
    if vector_value and vector_value[2] in codes:
        name, width = codes[vector_value[2]]
        bits = vector_value[1].lower()
        events[name][timestamp] = bits.rjust(width, bits[0] if bits[0] in 'xz' else '0')
    elif real_value and real_value[2] in codes:
        events[codes[real_value[2]][0]][timestamp] = float(real_value[1])
    elif scalar_value and scalar_value[2] in codes:
        events[codes[scalar_value[2]][0]][timestamp] = scalar_value[1].lower()
histories = {}
for name, changes in events.items():
    history = []
    for when, value in sorted(changes.items()):
        if not history or history[-1][1] != value:
            history.append((when, value))
    histories[name] = history
if histories != expected:
    test.error(f'Event time VCD mismatch: {histories}, expected {expected}')
print('Event time trace checks: 6')
test.passes()
