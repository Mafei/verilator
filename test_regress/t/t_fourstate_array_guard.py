#!/usr/bin/env python3
# DESCRIPTION: Verilator: Preserve known index facts inside array bounds guards
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of either the GNU Lesser General Public License Version 3
# or the Perl Artistic License Version 2.0.
# SPDX-FileCopyrightText: 2026 Mafei
# SPDX-License-Identifier: LGPL-3.0-only OR Artistic-2.0

import re
import vltest_bootstrap

test.scenarios('vlt')

test.compile(
    make_top_shell=False,
    make_main=False,
    verilator_flags2=[
        '--binary',
        '--fourstate',
        '-Wno-FUTURE',
        '--trace',
        '--top-module',
        't',
        '-j',
        '1',
        '-MAKEFLAGS',
        'VM_PARALLEL_BUILDS=1',
        '--output-split',
        '10000',
        '--output-split-cfuncs',
        '50',
    ],
)
log = test.obj_dir + '/run.log'
test.execute(executable=test.obj_dir + '/' + test.vm_prefix, logfile=log, check_finished=False)
test.file_grep_not(log, r'%Error|ERROR:|%Fatal')
words = [format(value, '033b') for value in (0x11, 0x22, 0x33)]
report = 'ARRAY_GUARD first=' + words[0] + ' middle=' + words[1] + ' last=' + words[2]
test.file_grep_count(log, '^' + report + '$', 1)
test.file_grep_count(log, r'^ARRAY_GUARD_PASS$', 1)

# Array VCD names include their unpacked index. Keep every physical value record;
# this independent oracle also checks that simulation reaches the final time.
expected = {'t.u.bank[' + str(index) + ']': [(0, word)] for index, word in zip((-2, -1, 0), words)}
actual = {name: [] for name in expected}
scopes = []
codes = {}
timestamp = 0
with open(test.trace_filename, encoding='ascii') as stream:
    trace = stream.read()
if not re.search(r'\$timescale\s+1ps\s+\$end', trace):
    test.error('Array guard VCD does not use 1ps precision')
for line in trace.splitlines():
    parts = line.split()
    if not parts:
        continue
    if parts[0] == '$scope':
        scopes.append(parts[2])
    elif parts[0] == '$upscope':
        scopes.pop()
    elif parts[0] == '$var':
        name = '.'.join(scopes + [parts[4]])
        if name in expected:
            if int(parts[2]) != 33:
                test.error('Array guard VCD width differs: ' + name)
            codes.setdefault(parts[3], []).append(name)
    elif parts[0].startswith('#'):
        next_time = int(parts[0][1:])
        if next_time < timestamp:
            test.error('Array guard VCD time moved backwards')
        timestamp = next_time
    elif parts[0].startswith('b') and len(parts) == 2:
        token = parts[0][1:].lower()
        for name in codes.get(parts[1], []):
            if not token or len(token) > 33 or set(token) - set('01xz'):
                test.error('Array guard VCD value is invalid: ' + name)
            value = token.rjust(33, token[0] if token[0] in 'xz' else '0')
            actual[name].append((timestamp, value))
if actual != expected or timestamp != 1:
    test.error(f'Array guard complete VCD histories differ: {actual}, final time {timestamp}')

test.passes()
