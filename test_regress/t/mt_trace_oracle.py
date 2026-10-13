#!/usr/bin/env python3
# DESCRIPTION: Verilator: Literal complete-history oracle for the MT trace control
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0
"""Compare every selected VCD record without removing transitions or repeats."""

import re
from pathlib import Path


def verify(log_path, wave_path, fourstate):  # pylint: disable=too-many-locals
    """Require exact six runtime observations and every clock/value/phase record."""
    width = 33
    zero, one = '0' * width, '1' * width
    xvalue = 'x' * width if fourstate else zero
    zvalue = 'z' * width if fourstate else zero
    mixed = ('10xz01' if fourstate else '100001').rjust(width, '0')
    prior = [zero, one, xvalue, zvalue, mixed, zero]
    log = Path(log_path).read_text(encoding='ascii')
    observed = re.findall(r'^MT_TRACE phase=(\d+) observed=([01xz]+)$', log, re.MULTILINE)
    assert observed == [(str(index), value) for index, value in enumerate(prior)]
    assert re.findall(r'^MT_FINAL phase=(\d+) sample=([01xz]+)$', log,
                      re.MULTILINE) == [('6', one)]
    assert log.count('*-* All Finished *-*') == 1
    expected = {
        'sample': [[0, zero], [1, one], [3, xvalue], *([[5, zvalue]] if fourstate else []),
                   [7, mixed], [9, zero], [11, one]],
        'phase': [[0, '0' * 32],
                  *[[2 * index - 1, format(index, '032b')] for index in range(1, 7)]],
        'clk': [[time, str(time % 2)] for time in range(12)]
    }
    widths = {'sample': 33, 'phase': 32, 'clk': 1}
    codes, declared, aliases = {}, {}, []
    scopes = []
    actual = {key: [] for key in expected}
    timestamp = 0
    text = Path(wave_path).read_text(encoding='ascii')
    assert re.search(r'\$timescale\s+1ps\s+\$end', text)
    assert '$enddefinitions $end' in text and text.endswith('\n')
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == '$scope':
            scopes.append(fields[2])
        elif fields[0] == '$upscope':
            scopes.pop()
        elif fields[0] == '$var' and fields[4] in expected:
            name = fields[4]
            full_name = '.'.join([*scopes, name])
            assert int(fields[2]) == widths[name]
            if name in declared:
                assert declared[name]['code'] == fields[3], 'Distinct same-named signals'
                aliases.append(full_name)
            else:
                declared[name] = {'path': full_name, 'code': fields[3], 'width': int(fields[2])}
                codes[fields[3]] = name
        elif line.startswith('#'):
            new_time = int(line[1:])
            assert new_time >= timestamp
            timestamp = new_time
        elif line.startswith('b') and len(fields) == 2 and fields[1] in codes:
            name = codes[fields[1]]
            value = fields[0][1:].lower()
            assert value and set(value) <= set('01xz') and len(value) <= widths[name]
            actual[name].append(
                [timestamp,
                 value.rjust(widths[name], value[0] if value[0] in 'xz' else '0')])
        elif line[0].lower() in '01xz' and line[1:] in codes:
            name = codes[line[1:]]
            assert widths[name] == 1
            actual[name].append([timestamp, line[0].lower()])
    assert set(declared) == set(expected) and timestamp == 11
    assert actual == expected, str(actual)
    return {
        'profile': 'four_state' if fourstate else 'two_state',
        'runtime_observations': len(observed),
        'complete_histories': len(actual),
        'complete_records': sum(len(value) for value in actual.values()),
        'declarations': declared,
        'same_code_declaration_aliases': aliases
    }
