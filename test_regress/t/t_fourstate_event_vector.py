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
test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '-Wno-FUTURE'])
test.execute(logfile=test.run_log_filename)
test.file_grep(test.run_log_filename, r'Vector event checks: (\d+)', 755)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')

# Build an independent mathematical oracle for the 33-bit scalar vector.
bits = ['0'] * 33
vector_events = {0: ''.join(bits)}
for when, bit, value in ((2, 32, '1'), (4, 32, '0'), (5, 31, 'z'), (6, 31, 'x'),
                         (7, 31, 'z'), (10, 0, '1'), (11, 32, 'x'), (12, 0, '0'),
                         (15, 32, '0'), (16, 31, '0')):
    bits[bit] = value
    vector_events[when] = ''.join(reversed(bits))
vector_times = (2, 4, 5, 6, 7, 10, 11, 12, 15, 16)
mixed_times = (2, 4, 5, 6, 7, 9, 10, 11, 12, 13, 15, 16)
edge_times = {'rise': (10,), 'fall': (12,), 'both': (10, 12)}
expected = {
    'vector': list(vector_events.items()),
    'scalar': [(0, '0'), (9, '1'), (13, '0')],
}
widths = {'vector': 33, 'scalar': 1}
for stem, times in {'vector': vector_times, 'mixed': mixed_times, **edge_times}.items():
    expected[stem + '_events'] = [(0, '0' * 32)] + [(when, format(count, '032b'))
                                                  for count, when in enumerate(times, start=1)]
    expected[stem + '_time'] = [(0, '0' * 64)] + [(when, format(when, '064b')) for when in times]
    widths[stem + '_events'] = 32
    widths[stem + '_time'] = 64

with open(test.trace_filename, encoding='ascii') as stream:
    trace = stream.read()
if not re.search(r'\$timescale\s+1ps\s+\$end', trace):
    test.error('Vector event trace does not use the expected 1ps precision')
scopes = []
codes = {}
events = {name: {} for name in expected}
timestamp = 0
for line in trace.splitlines():
    line = line.lstrip()
    scope = re.match(r'\$scope \w+ (\S+) \$end', line)
    if scope:
        scopes.append(scope[1])
    if line.startswith('$upscope'):
        scopes.pop()
    declaration = re.match(r'\$var \w+ (\d+) (\S+) (\w+) ', line)
    if declaration and 'w33' in scopes and declaration[3] in expected:
        name = declaration[3]
        if int(declaration[1]) == widths[name]:
            codes.setdefault(declaration[2], []).append(name)
    if line.startswith('#'):
        timestamp = int(line[1:])
    value = re.match(r'b([01xzXZ]+) (\S+)', line)
    scalar = re.match(r'([01xzXZ])(\S+)$', line)
    if value or scalar:
        match = value or scalar
        bits, code = match[1].lower(), match[2]
        for name in codes.get(code, []):
            events[name][timestamp] = bits.rjust(widths[name], bits[0] if bits[0] in 'xz' else '0')
histories = {}
for name, changes in events.items():
    history = []
    for when, bits in sorted(changes.items()):
        if not history or history[-1][1] != bits:
            history.append((when, bits))
    histories[name] = history
if histories != expected:
    test.error(f'Vector event scalar VCD mismatch: {histories}, expected {expected}')
print('Vector event trace checks: 12')
test.passes()
