#!/usr/bin/env python3
# DESCRIPTION: Verilator: Verilog Test driver/expect definition
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Wilson Snyder
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

"""Independent character-vector oracle for the bounded resolver regressions."""

import re

STATES = '01xz'
PAIR = {
    'wire': '0xx0x1x1xxxx01xz',
    'tri': '0xx0x1x1xxxx01xz',
    'wor': '01x01111x1xx01xz',
    'wand': '000001x10xxx01xz',
}
TRIPLE = {
    'wire': ('0xx0xxxxxxxx0xx0' 'xxxxx1x1xxxxx1x1'
             'xxxxxxxxxxxxxxxx' '0xx0x1x1xxxx01xz'),
    'tri': ('0xx0xxxxxxxx0xx0' 'xxxxx1x1xxxxx1x1'
            'xxxxxxxxxxxxxxxx' '0xx0x1x1xxxx01xz'),
    'wor': ('01x01111x1xx01x0' '1111111111111111'
            'x1xx1111x1xxx1xx' '01x01111x1xx01xz'),
    'wand': ('0000000000000000' '000001x10xxx01x1'
             '00000xxx0xxx0xxx' '000001x10xxx01xz'),
}
WIDTHS = (1, 7, 33, 65, 95, 129)


def resolved(net, *sources):
    table = PAIR[net] if len(sources) == 2 else TRIPLE[net]
    result = []
    for chars in zip(*sources):
        index = 0
        for char in chars:
            index = index * 4 + STATES.index(char)
        result.append(table[index])
    return ''.join(result)


def append(expected, key, timestamp, value):
    if expected[key][-1][1] != value:
        expected[key].append((timestamp, value))


def add(expected, widths, key, width, value):
    widths[key] = width
    expected[key] = [(0, value)]


def _declaration(scopes, line, expected, widths):
    declaration = re.match(r'\$var (\w+) (\d+) (\S+) (\w+) ', line)
    if not declaration:
        return None
    keys = []
    for depth in range(len(scopes)):
        key = '.'.join(scopes[depth:] + [declaration[4]])
        if key in expected:
            width_ok = (declaration[1] == 'real' if widths[key] == 0
                        else int(declaration[2]) == widths[key])
            if width_ok:
                keys.append(key)
    return declaration[3], keys


def _value(line):
    match = (re.match(r'b([01xzXZ]+) (\S+)', line)
             or re.match(r'([01xzXZ])(\S+)$', line)
             or re.match(r'r([^ ]+) (\S+)', line))
    return match.groups() if match else None


def _changes(trace, expected, widths):
    scopes = []
    codes = {}
    changes = {key: {} for key in expected}
    timestamp = 0
    for line in trace.splitlines():
        line = line.lstrip()
        scope = re.match(r'\$scope \w+ (\S+) \$end', line)
        if scope:
            scopes.append(scope[1])
        if line.startswith('$upscope'):
            scopes.pop()
        declaration = _declaration(scopes, line, expected, widths)
        if declaration:
            codes.setdefault(declaration[0], []).extend(declaration[1])
        if line.startswith('#'):
            timestamp = int(line[1:])
        if (line and line[0] not in '$#br' and line[1:] in codes
                and line[0].lower() not in STATES):
            raise ValueError(f'Resolver VCD has invalid scalar value: {line!r} at {timestamp}ps')
        match = _value(line)
        if match:
            for key in codes.get(match[1], []):
                value = match[0].lower()
                if widths[key] == 0:
                    value = str(float(value)).removesuffix('.0')
                else:
                    value = value.rjust(widths[key], value[0] if value[0] in 'xz' else '0')
                    if len(value) != widths[key]:
                        raise ValueError(f'Resolver VCD width mismatch for {key}: {value}')
                changes[key][timestamp] = value
    return changes


def check_trace(test, expected, widths):
    with open(test.trace_filename, encoding='ascii') as stream:
        trace = stream.read()
    if not re.search(r'\$timescale\s+1ps\s+\$end', trace):
        test.error('Resolver trace does not use 1ps precision')
    try:
        changes = _changes(trace, expected, widths)
    except ValueError as error:
        test.error(str(error))
        return
    actual = {}
    # A VCD has physical timestamps, not delta-cycle numbers. Check the final
    # complete value at every timestamp; SV event counters additionally detect
    # artificial transitions introduced by separately updating internal halves.
    for key, values in changes.items():
        history = []
        for timestamp, value in sorted(values.items()):
            if not history or history[-1][1] != value:
                history.append((timestamp, value))
        actual[key] = history
    if actual != expected:
        mismatches = {key: {'got': actual[key], 'expected': value}
                      for key, value in expected.items() if actual[key] != value}
        test.error(f'Resolver VCD mismatch: {mismatches}')
    print(f'Resolver trace checks: {len(expected)}')
