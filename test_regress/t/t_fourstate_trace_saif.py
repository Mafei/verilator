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

test.top_filename = 't/t_fourstate_trace.v'

test.compile(verilator_flags2=['--binary', '--fourstate', '-Wno-FUTURE', '--trace-saif'])

test.execute()

# Derive residence times from t_fourstate_trace.v before comparing the golden.
# Its logic bits start X, then spend 10 ticks each at 1, 0, Z, and X.
with open(test.trace_filename, encoding='utf-8') as stream:
    contents = stream.read()
duration = re.search(r'\(DURATION (\d+)\)', contents)
if not duration or int(duration[1]) != 50:
    test.error('Wrong four-state SAIF duration')
records = {}
for name, fields in re.findall(r'\((\w+(?:\\\[\d+\\\])?) ((?:\([A-Z0-9]+ \d+\) ?)+)\)', contents):
    records[name.replace('\\', '')] = {
        key: int(value)
        for key, value in re.findall(r'\(([A-Z0-9]+) (\d+)\)', fields)
    }
expected_names = set()
widths = (1, 8, 9, 32, 33, 64, 65, 128, 129, 256, 257, 301)
for signal, width in enumerate(widths):
    for bit in range(width):
        name = f's{signal}' + (f'[{bit}]' if width > 1 else '')
        expected_names.add(name)
        # TC retains encoded-state changes, including the initial X sample.
        expected = {
            'T0': 10 if bit == 0 else 20,
            'T1': 10 if bit == 0 else 0,
            'TX': 20,
            'TZ': 10,
            'TB': 0,
            'TC': 5 if bit == 0 else 4
        }
        if records.get(name) != expected:
            test.error(f'Four-state SAIF {name}: {records.get(name)}, expected {expected}')
        if sum(records[name][field] for field in ('T0', 'T1', 'TX', 'TZ')) != 50:
            test.error(f'Four-state SAIF {name}: state times do not sum to DURATION')
for bit in range(14):
    name = f'foo[{bit}]'
    expected_names.add(name)
    expected = {
        'T0': 40 if bit == 0 else 50,
        'T1': 10 if bit == 0 else 0,
        'TX': 0,
        'TZ': 0,
        'TB': 0,
        'TC': 2 if bit == 0 else 0
    }
    if records.get(name) != expected:
        test.error(f'Two-state SAIF {name}: {records.get(name)}, expected {expected}')
if set(records) != expected_names:
    test.error('Unexpected or missing four-state SAIF nets')
print(f'SAIF fixture oracle: {len(expected_names)} bit records')

test.saif_identical(test.trace_filename, test.golden_filename)

test.passes()
