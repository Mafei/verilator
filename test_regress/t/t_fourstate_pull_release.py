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
# Ascending packed ranges are intentional coverage for the same pull semantics.
test.compile(verilator_flags2=['--binary', '--fourstate', '--trace', '--stats', '-Wno-FUTURE',
                              '-Wno-ASCRANGE'])
if test.vlt_all:
    test.file_grep(test.stats, r'Fourstate, Implicit pull driver fallbacks\s+(\d+)', 18)
test.execute(logfile=test.run_log_filename)
test.file_grep(test.run_log_filename, r'Pull release checks: (\d+)', 4032)
test.file_grep_not(test.run_log_filename, r'%Error|ERROR:|WARNING:')


def stimulus(width, phase):
    # This independent oracle uses character vectors; it does not inspect
    # generated C++ or obtain expected values from either simulator.
    uniform = {**dict.fromkeys((0, 4, 16, 22, 25, 31), '0'),
               **dict.fromkeys((1, 6, 30), '1'),
               **dict.fromkeys((2, 8, 24), 'x'),
               **dict.fromkeys((3, 5, 7, 9, 10, 23, 29), 'z')}
    if phase in uniform:
        return uniform[phase] * width
    if phase in (11, 12, 13, 14, 15, 26, 27):
        offset = min(phase - 11, 3) if 12 <= phase <= 15 else 0
        return ''.join('01xz'[(bit + offset) % 4] for bit in reversed(range(width)))
    upper = {17: 'z', 18: 'x', 19: 'z', 20: 'z', 21: '1'}
    if phase in upper:
        return upper[phase] + '0' * (width - 1)
    if phase == 28:
        return ''.join('1' if bit % 3 == 1 else '0' for bit in reversed(range(width)))
    raise ValueError(f'Unknown stimulus phase {phase}')


instances = {'w1': 1, 'w7': 7, 'w33': 33, 'w65': 65, 'w95': 95, 'w129': 129,
             'ascending': 7, 'nonzero': 33}
expected = {}
widths = {}
for instance, width in instances.items():
    signals = {
        'driver': (width, '0' * width),
        'default_down': (width, '0' * width),
        'default_up': (width, '1' * width),
    }
    for stem in ('down', 'up'):
        signals.update({stem: (width, '0' * width),
                        stem + '_snapshot': (width, '0' * width),
                        stem + '_events': (32, '0' * 32),
                        stem + '_time': (64, '0' * 64),
                        stem + '_realtime': (0, '0')})
    for name, (bits, initial) in signals.items():
        key = instance + '.' + name
        expected[key] = [(0, initial)]
        widths[key] = bits
    counts = {'down': 0, 'up': 0}
    for phase in range(32):
        timestamp = 1125 + phase * 125
        source = stimulus(width, phase)
        key = instance + '.driver'
        if source != expected[key][-1][1]:
            expected[key].append((timestamp, source))
        for stem, pull in (('down', '0'), ('up', '1')):
            resolved = source.replace('z', pull)
            key = instance + '.' + stem
            if resolved != expected[key][-1][1]:
                counts[stem] += 1
                expected[key].append((timestamp, resolved))
                expected[key + '_snapshot'].append((timestamp, resolved))
                expected[key + '_events'].append((timestamp, format(counts[stem], '032b')))
                # $time rounds to integral nanoseconds, whereas $realtime
                # retains the exact 1ps precision, including half-nanosecond ties.
                rounded = (timestamp + 500) // 1000
                time_bits = format(rounded, '064b')
                if expected[key + '_time'][-1][1] != time_bits:
                    expected[key + '_time'].append((timestamp, time_bits))
                expected[key + '_realtime'].append((timestamp, str(timestamp / 1000).removesuffix('.0')))

# A ninth same-scope instance has independent, staggered RHS signals.
# This catches accidental capture sharing between separate assignments.
for source in ('source_a', 'source_b'):
    key = 'distinct.' + source
    widths[key] = 65
    expected[key] = [(0, '0' * 65)]
for stem in ('down', 'up'):
    for name, width in ((stem, 65), (stem + '_snapshot', 65), (stem + '_events', 32),
                        (stem + '_time', 64), (stem + '_realtime', 0)):
        key = 'distinct.' + name
        widths[key] = width
        expected[key] = [(0, '0' * width if width else '0')]
for phase in range(8):
    for stage, stem, source_name, pull in ((0, 'down', 'source_a', '0'),
                                           (1, 'up', 'source_b', '1')):
        timestamp = 1125 + phase * 125 + stage * 50
        if phase == 3:
            source = ''.join('01xz'[(bit + stage * 2) % 4] for bit in reversed(range(65)))
        else:
            source = ('zx1?0zzx' if stage == 0 else 'xz0?1xxz')[phase] * 65
        key = 'distinct.' + source_name
        if source != expected[key][-1][1]:
            expected[key].append((timestamp, source))
        key = 'distinct.' + stem
        resolved = source.replace('z', pull)
        if resolved != expected[key][-1][1]:
            expected[key].append((timestamp, resolved))
            expected[key + '_snapshot'].append((timestamp, resolved))
            count = len(expected[key]) - 1
            expected[key + '_events'].append((timestamp, format(count, '032b')))
            time_bits = format((timestamp + 500) // 1000, '064b')
            if expected[key + '_time'][-1][1] != time_bits:
                expected[key + '_time'].append((timestamp, time_bits))
            expected[key + '_realtime'].append((timestamp, str(timestamp / 1000).removesuffix('.0')))
instances['distinct'] = 65

with open(test.trace_filename, encoding='ascii') as stream:
    trace = stream.read()
if not re.search(r'\$timescale\s+1ps\s+\$end', trace):
    test.error('Pull release trace does not use the expected 1ps precision')
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
    declaration = re.match(r'\$var (\w+) (\d+) (\S+) (\w+) ', line)
    if declaration:
        owner = next((name for name in instances if name in scopes), None)
        key = owner + '.' + declaration[4] if owner else ''
        if key in expected:
            is_real = declaration[1] == 'real'
            width_matches = is_real if widths[key] == 0 else int(declaration[2]) == widths[key]
            if width_matches:
                codes.setdefault(declaration[3], []).append(key)
    if line.startswith('#'):
        timestamp = int(line[1:])
    value = re.match(r'b([01xzXZ]+) (\S+)', line)
    scalar = re.match(r'([01xzXZ])(\S+)$', line)
    real_value = re.match(r'r([^ ]+) (\S+)', line)
    if value or scalar or real_value:
        match = value or scalar or real_value
        for key in codes.get(match[2], []):
            bits = match[1].lower()
            if widths[key] == 0:
                bits = str(float(bits)).removesuffix('.0')
            else:
                bits = bits.rjust(widths[key], bits[0] if bits[0] in 'xz' else '0')
            events[key][timestamp] = bits
histories = {}
for key, changes in events.items():
    history = []
    for when, bits in sorted(changes.items()):
        if not history or history[-1][1] != bits:
            history.append((when, bits))
    histories[key] = history
if histories != expected:
    mismatches = {key: {'got': histories[key], 'expected': wanted}
                  for key, wanted in expected.items() if histories[key] != wanted}
    test.error(f'Pull release VCD mismatch: {mismatches}')
print(f'Pull release trace checks: {len(expected)}')
test.passes()
