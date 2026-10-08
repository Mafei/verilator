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
fourstate = test.name == 't_fourstate_nba_loop'
# All runtime delay choices are positive (10, 8 or 4 ticks).
flags = ['--binary', '--trace', '--no-sched-zero-delay']
if fourstate:
    flags += ['--fourstate', '-Wno-FUTURE']
test.compile(verilator_flags2=flags)
test.execute(logfile=test.run_log_filename)
test.file_grep(test.run_log_filename, r'NBA checks: (\d+)', 317)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')


def pattern(kind):
    if kind == 3:
        return ['1' if bit % 3 == 1 else '0' for bit in range(33)]
    cycles = ('xz01', 'zx10', '1xz0') if fourstate else ('0101', '1010', '1100')
    return [cycles[kind][bit % 4] for bit in range(33)]


def vector(bits):
    return ''.join(reversed(bits))


seed = pattern(0)
looped = seed.copy()
looped[:31] = pattern(1)[:31]
captured = seed.copy()
captured[30:33] = pattern(1)[30:33]
ordered = pattern(1)
ordered[30:33] = list(reversed('zx1' if fourstate else '010'))
ordered[0] = 'x' if fourstate else '0'
different_early = seed.copy()
different_early[0] = 'z' if fourstate else '1'
different_late = seed.copy()
different_late[0] = 'x' if fourstate else '0'
disjoint = seed.copy()
disjoint[0] = 'z' if fourstate else '1'
disjoint[32] = '1'
upper = 'x' * 16 if fourstate else format(0xc35a, '016b')
repeat_upper = 'x' * 16 if fourstate else format(0x5ac3, '016b')
repeat_second = '00111100zzzz0001' if fourstate else format(0x3c91, '016b')
expected = {
    'out': [(0, upper + ('x' * 16 if fourstate else '0' * 16)),
            (200, upper + format(0x5678, '016b'))],
    'repeat_out': [(0, repeat_upper + ('x' * 16 if fourstate else '0' * 16)),
                   (48, repeat_upper + format(0x0f0f, '016b')), (50, repeat_upper + repeat_second)],
    'looped': [(0, vector(seed)), (5, vector(looped))],
    'captured': [(0, vector(seed)), (8, vector(captured))],
    'ordered': [(0, vector(seed)), (12, vector(ordered))],
    'ordered_rev': [(0, vector(seed)), (12, vector(pattern(3)))],
    'different': [(0, vector(seed)), (15, vector(different_early)), (17, vector(different_late))],
    'nested': [(0, vector(seed)), (21, vector(captured))],
    'disjoint': [(0, vector(seed)), (21, vector(disjoint))],
    'q_same': [(0, vector(seed)), (28, vector(pattern(2)))],
    'q_due': [(0, vector(seed)), (26, vector(pattern(3))), (28, vector(pattern(1)))],
}

# Check independent scalar VCD histories, preserving X and Z and exact times.
# Multiple writes at one timestamp are compared after the final update there.
with open(test.trace_filename, encoding='ascii') as stream:
    trace = stream.read()
if not re.search(r'\$timescale\s+1ps\s+\$end', trace):
    test.error('NBA trace does not use the expected 1ps precision')
codes = {}
events = {name: {} for name in expected}
timestamp = 0
for line in trace.splitlines():
    line = line.lstrip()
    declaration = re.match(r'\$var \w+ (\d+) (\S+) (\w+) ', line)
    if declaration and declaration[3] in expected:
        width = int(declaration[1])
        wanted_width = 32 if declaration[3] in ('out', 'repeat_out') else 33
        if width == wanted_width:
            codes.setdefault(declaration[2], []).append((declaration[3], width))
    if line.startswith('#'):
        timestamp = int(line[1:])
    value = re.match(r'b([01xzXZ]+) (\S+)', line)
    if value and value[2] in codes:
        bits = value[1].lower()
        for name, width in codes[value[2]]:
            padded = bits.rjust(width, bits[0] if bits[0] in 'xz' else '0')
            events[name][timestamp] = padded
histories = {}
for name, changes in events.items():
    history = []
    for when, bits in sorted(changes.items()):
        if not history or history[-1][1] != bits:
            history.append((when, bits))
    histories[name] = history
if histories != expected:
    test.error(f'NBA scalar VCD mismatch: {histories}, expected {expected}')
print('NBA trace checks: 11')
test.passes()
