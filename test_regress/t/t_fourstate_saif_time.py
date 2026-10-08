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

test.scenarios('vlt_all')
test.top_filename = 't/t_trace_cat.v'

test.compile(make_main=False,
             verilator_flags2=[
                 '--exe', test.pli_filename, '--no-timing', '--trace-saif', '-CFLAGS', '-std=c++14'
             ])
test.execute()

# Independently integrate the public stimulus schedule, without using a golden
# file or the runtime's encoded value/XZ accumulator implementation.
widths = (1, 7, 15, 31, 33, 65, 95)
times = (0, 3, 8, 15, 26)
records_checked = 0
checks = 0
previous_tc = {}
for close_time, filename in ((26, 'simx_short.saif'), (39, 'simx.saif')):
    with open(test.obj_dir + '/' + filename, encoding='utf-8') as stream:
        contents = stream.read()
    duration = re.search(r'\(DURATION (\d+)\)', contents)
    if not duration or int(duration[1]) != close_time:
        test.error(f'Wrong SAIF duration in {filename}')
    records = {}
    for name, fields in re.findall(r'\((\w+(?:\\\[\d+\\\])?) ((?:\([A-Z0-9]+ \d+\) ?)+)\)',
                                   contents):
        records[name.replace('\\', '')] = {
            key: int(value)
            for key, value in re.findall(r'\(([A-Z0-9]+) (\d+)\)', fields)
        }
    expected_names = set()
    for kind in ('s', 'k'):
        states = ('0', '1', 'X', 'Z') if kind == 's' else ('0', '1')
        for width in widths:
            for bit in range(width):
                name = f'{kind}{width}' + (f'[{bit}]' if width > 1 else '')
                expected_names.add(name)
                expected = dict.fromkeys(('T0', 'T1', 'TX', 'TZ', 'TB', 'TC'), 0)
                previous = '0'
                for phase, start in enumerate(times):
                    state = states[(bit + phase) % len(states)]
                    end = times[phase + 1] if phase + 1 < len(times) else close_time
                    expected['T' + state] += end - start
                    # Retain the current encoded-state TC convention (including
                    # the initial sample), without inventing a close-time event.
                    expected['TC'] += int(state != previous)
                    previous = state
                actual = records.get(name)
                if not actual:
                    test.error(f'Missing SAIF bit {name} in {filename}')
                for field, value in expected.items():
                    if actual.get(field) != value:
                        test.error(
                            f'{filename} {name}: {field}={actual.get(field)}, expected {value}')
                    checks += 1
                if sum(actual[field] for field in ('T0', 'T1', 'TX', 'TZ')) != close_time:
                    test.error(f'{filename} {name}: state times do not sum to DURATION')
                checks += 1
                if close_time == 26:
                    previous_tc[name] = actual['TC']
                elif actual['TC'] != previous_tc[name]:
                    test.error(f'{name}: close-time residence interval changed TC')
                records_checked += 1
    if set(records) != expected_names:
        test.error(f'Unexpected or missing SAIF nets in {filename}')

print(f'SAIF oracle: {records_checked} bit records, {checks} checks')
test.passes()
